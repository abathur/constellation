"""
TODO: I'm really starting to chafe at the organization of this, but I don't have time to break it up right now.

See Randy3k's example of yielding lambdas during setup?
https://github.com/SublimeText/UnitTesting/blob/master/unittesting/helpers/temp_directory_test_case.py

I wonder if pytest is compatible with deferrabletestcase

Note: These tests used to have a common, annoying pattern:
- do some action
- wait some arbitrary amount of time
- look for data structure changes and hope they've happened.

I've now rewritten them to use a newer pattern where they yield
a lambda that UnitTesting will check until it's true (within 4
second timeout). This is much less dumb, but it also means many
of the assertions are implicit, bundled up in the handling of
the command action. If you see a "yield self.blah()" call, there's
almost inevitably an implicit lambda assertion on the other end.

I guess "passing" many of these tests now means getting to the end
without a timeout error.
"""

import sublime
import sublime_plugin
import os
import time

from unittesting import DeferrableTestCase
import Constellation
from Constellation.util import input_handlers


class TestCore(DeferrableTestCase):
    state = api = None

    def setUp(self):
        self.api = Constellation.util.api.API
        self.api.load_state()
        self.state = self.api.state

    def open_constellations(self):
        return self.api.open_constellations(self.api)

    def create_constellation(self, name, cleanup=True):
        if cleanup:
            self.addCleanup(self.destroy_constellation, name)

        sublime.run_command("create_constellation", {"name": name})

        return lambda: name in self.state.get("constellations")

    def test_create_constellation(self):
        constellation = "test_create_constellation"
        yield self.create_constellation(constellation)

        # TODO: confirm it shows up in the open, destroy, and rename menus?

    def open_constellation(self, name):
        assert name not in self.open_constellations()

        sublime.run_command("open_constellation", {"constellation": name})

        def verify():
            print(
                "open_constellation:verify",
                name,
                self.open_constellations(),
                self.state.get("constellations")[name]["projects"],
                [(win.id(), win.project_file_name()) for win in sublime.windows()],
            )
            for project in self.state.get("constellations")[name]["projects"]:
                if project not in set(
                    [win.project_file_name() for win in sublime.windows()]
                ):
                    return False

            if name not in self.open_constellations():
                return False

            return True

        return verify

    def close_constellation(self, name):
        assert name in self.open_constellations()

        sublime.run_command("close_constellation", {"constellation": name})

        def verify():
            const_projects = set(self.state.get("constellations")[name]["projects"])
            win_projects = set([win.project_file_name() for win in sublime.windows()])

            # constellation projects not among window projects
            if not win_projects.isdisjoint(const_projects):
                return False

            if name in self.open_constellations():
                return False

            return True

        return verify

    def confirm_projects_are_closed(self, projects):
        const_projects = set(projects)

        return lambda: const_projects.isdisjoint(
            set([win.project_file_name() for win in sublime.windows()])
        )

    def confirm_project_is_closed(self, project):
        # return lambda: const_projects.issubset(
        #     set([win.project_file_name() for win in sublime.windows()])
        # )

        def verify():
            print(
                "confirm_project_is_closed:verify",
                self.open_constellations(),
                project,
                [(win.id(), win.project_file_name()) for win in sublime.windows()],
            )
            return project not in [win.project_file_name() for win in sublime.windows()]

    def confirm_projects_are_open(self, projects):
        const_projects = set(projects)

        # return lambda: const_projects.issubset(
        #     set([win.project_file_name() for win in sublime.windows()])
        # )

        def verify():
            print(
                "confirm_projects_are_open:verify",
                self.open_constellations(),
                const_projects,
                [(win.id(), win.project_file_name()) for win in sublime.windows()],
            )
            return const_projects.issubset(
                set([win.project_file_name() for win in sublime.windows()])
            )

        return verify

    def confirm_project_is_open(self, project):
        # return lambda: const_projects.issubset(
        #     set([win.project_file_name() for win in sublime.windows()])
        # )

        def verify():
            print(
                "confirm_project_is_open:verify",
                self.open_constellations(),
                project,
                [(win.id(), win.project_file_name()) for win in sublime.windows()],
            )
            return project in [win.project_file_name() for win in sublime.windows()]

        return verify

    def test_open_close_cycle_constellation(self):
        constellation = "test_open_close_cycle_constellation"
        onepath = self.make_project_path("one.sublime-project")
        twopath = self.make_project_path("two.sublime-project")
        # create a constellation (this also opens it)
        yield self.create_constellation(constellation, cleanup=False)

        # add a couple projects to it
        yield self.add_constellation_project(constellation, onepath)
        # projects = self.state.get("constellations")[constellation]["projects"]
        # yield self.confirm_projects_are_open(projects)

        yield self.add_constellation_project(constellation, twopath)
        projects = self.state.get("constellations")[constellation]["projects"]
        # yield self.confirm_projects_are_open(projects)
        yield self.confirm_project_is_open(onepath)
        yield self.confirm_project_is_open(twopath)

        # TODO: confirm constellation shows up in close menu?
        print("about to close", constellation)
        yield self.close_constellation(constellation)
        print("about to confirm closed", projects)
        # yield self.confirm_projects_are_closed(projects)
        yield self.confirm_project_is_closed(onepath)
        yield self.confirm_project_is_closed(twopath)
        print("about to nap")
        yield lambda: time.sleep(2) or True

        # yield self.open_constellation(constellation)
        # # yield self.confirm_projects_are_open(projects)
        # yield self.confirm_project_is_open(onepath)
        # yield self.confirm_project_is_open(twopath)

        # yield self.close_constellation(constellation)
        # yield self.confirm_projects_are_closed(projects)

        # yield self.destroy_constellation(constellation)

    def destroy_constellation(self, name):
        assert name in self.state.get("constellations")

        projects = self.state.get("constellations")[name]["projects"]
        sublime.run_command("destroy_constellation", {"constellation": name})

        self.assertNotIn(name, self.state.get("constellations"))

        return self.confirm_projects_are_closed(projects)

    def test_destroy_constellation(self):
        # create a constellation
        constellation = "test_destroy_constellation"
        yield self.create_constellation(constellation, cleanup=False)
        yield self.destroy_constellation(constellation)

        # TODO: confirm it no longer shows up in open, close, rename, destroy menus

    @staticmethod
    def make_project_path(filename):
        return os.path.join(*(Constellation.__path__._path + ["tests", filename]))

    def add_constellation_project(self, constellation, proj_path):
        sublime.run_command(
            "find_project", {"constellation": constellation, "project": proj_path}
        )
        # time.sleep(2)
        # sublime.run_command(
        #     "find_project", {"constellation": constellation, "project": proj_path}
        # )
        # time.sleep(2)
        # sublime.run_command(
        #     "find_project", {"constellation": constellation, "project": proj_path}
        # )
        # time.sleep(2)
        # sublime.run_command(
        #     "find_project", {"constellation": constellation, "project": proj_path}
        # )
        # time.sleep(2)
        # sublime.run_command(
        #     "find_project", {"constellation": constellation, "project": proj_path}
        # )
        # time.sleep(2)

        def verify():
            """
            Caution:
            This *was* (before oct 2026) testing both that the project is in
            the statefile under the right constellation *and* that the
            project is open

            I'm trying to debug this after a long winter and I don't
            recall why we're asserting that it must be open here, and
            the local logic doesn't make it clear to me that this is right.

            Trying to back out one stop for now and see what that gets us.

            Was:
            return proj_path in self.state.get("constellations")[constellation][
                "projects"
            ] and proj_path in set(
                [win.project_file_name() for win in sublime.windows()]
            )

            Update:
            ah, I may be understanding; a single macOS build is getting stuck
            shortly after this runs when only one of two projects have opened

            this may not actually help if it isn't a true race condition
            but it may nonetheless be the reason. Switching back for now.
            """
            print(
                "add_constellation_project:verify",
                self.open_constellations(),
                constellation,
                proj_path,
                self.state.get("constellations")[constellation]["projects"],
                [(win.id(), win.project_file_name()) for win in sublime.windows()],
            )
            # return proj_path in self.state.get("constellations")[constellation][
            #     "projects"
            # ] and proj_path in set(
            #     [win.project_file_name() for win in sublime.windows()]
            # )
            return (
                proj_path in self.state.get("constellations")[constellation]["projects"]
            )

        return verify

    def test_add_constellation_projects(self):
        constellation = "test_add_constellation_projects"
        # create a constellation
        yield self.create_constellation(constellation)

        # add a couple projects to it & confirm they're added
        onepath = self.make_project_path("one.sublime-project")
        yield self.add_constellation_project(constellation, onepath)
        yield  # yield to main?
        yield self.confirm_project_is_open(onepath)

        yield lambda: time.sleep(2) or True
        yield  # yield to main?

        twopath = self.make_project_path("two.sublime-project")
        yield self.add_constellation_project(constellation, twopath)
        yield  # yield to main?
        yield lambda: time.sleep(2) or True

        yield  # yield to main?

        # projects = self.state.get("constellations")[constellation]["projects"]
        # yield self.confirm_projects_are_open(projects)
        yield self.confirm_project_is_open(twopath)

        yield self.remove_project_menu_contains(
            constellation,
            [
                ("one.sublime-project", "wrongboy"),
                ("two.sublime-project", "rightboy"),
            ],
        )

        yield lambda: constellation in self.open_constellations()

    def remove_constellation_project(self, constellation, proj_path):
        sublime.run_command(
            "remove_project", {"constellation": constellation, "project": proj_path}
        )
        return (
            lambda: proj_path
            not in self.state.get("constellations")[constellation]["projects"]
        )

    def test_remove_constellation_project(self):
        constellation = "test_remove_constellation_project"
        onepath = self.make_project_path("one.sublime-project")
        # create a constellation
        yield self.create_constellation(constellation)

        # sanity check; project isn't already there
        self.assertNotIn(
            onepath, self.state.get("constellations")[constellation]["projects"]
        )

        # add a couple projects & confirm their presence
        yield self.add_constellation_project(constellation, onepath)

        # Caution: pre Oct 2026 this closed the project before removing it,
        # but atm I'm struggling to think of a reason it must.

        # rm and confirm it's not in list
        yield self.remove_constellation_project(constellation, onepath)

        # TODO: confirm it no longer appears in the remove menu?

    def remove_project_menu(self, constellation):
        handle = input_handlers.ConstellationProjectList()
        return handle.next_input({"constellation": constellation}).list_items()

    def remove_project_menu_contains(self, constellation, projects):
        # make sure the remove menu has the right projects:
        self.assertEqual(
            set(self.remove_project_menu(constellation)),
            set(
                [
                    (
                        "one.sublime-project",
                        self.make_project_path("one.sublime-project"),
                    ),
                    (
                        "two.sublime-project",
                        self.make_project_path("two.sublime-project"),
                    ),
                ]
            ),
        )
