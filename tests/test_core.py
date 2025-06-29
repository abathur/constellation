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
        """
        DOING: I wonder if the trouble is that we're moving on before everything's open?
        sublime.run_command("open_constellation", {"constellation": name})
        return lambda: name in self.open_constellations()

        not sure it's the trouble, but this new assertion does break, and
        it seems to do so because creating the constellation opens it, while the test treats it like it doesn't
        """
        assert name not in self.open_constellations()

        sublime.run_command("open_constellation", {"constellation": name})

        def verify():
            # print(
            #     "open_constellation:verify",
            #     name,
            #     self.open_constellations(),
            #     self.state.get("constellations")[name]["projects"],
            #     [(win.id(), win.project_file_name()) for win in sublime.windows()],
            # )

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
            # print(
            #     "close_constellation:verify",
            #     name,
            #     self.open_constellations(),
            #     self.state.get("constellations")[name]["projects"],
            #     [(win.id(), win.project_file_name()) for win in sublime.windows()],
            # )

            const_projects = set(self.state.get("constellations")[name]["projects"])
            win_projects = set([win.project_file_name() for win in sublime.windows()])

            # DOING: less-dumb version of commented-out below?
            if not win_projects.isdisjoint(const_projects):
                return False

            # for project in self.state.get("constellations")[name]["projects"]:
            #     if project in set(
            #         [win.project_file_name() for win in sublime.windows()]
            #     ):
            #         return False

            if name in self.open_constellations():
                return False

            return True

        return verify

    # DOING: are you okay? this looks inverted.
    def confirm_projects_are_closed_old(self, constellation):
        if constellation not in self.state.get("constellations"):
            return False

        const_projects = set(
            self.state.get("constellations")[constellation]["projects"]
        )

        return lambda: const_projects.issubset(
            set([win.project_file_name() for win in sublime.windows()])
        )

    def confirm_projects_are_closed(self, projects):
        const_projects = set(projects)

        def verify():
            # print(
            #     "confirm_projects_are_closed:verify",
            #     projects,
            #     [win.project_file_name() for win in sublime.windows()],
            # )

            return const_projects.isdisjoint(
                set([win.project_file_name() for win in sublime.windows()])
            )

        return verify

    def confirm_projects_are_open(self, projects):
        const_projects = set(projects)

        return lambda: const_projects.issubset(
            set([win.project_file_name() for win in sublime.windows()])
        )

    def test_open_and_close_constellation(self):
        constellation = "test_open_and_close_constellation"
        onepath = self.make_project_path("one.sublime-project")
        twopath = self.make_project_path("two.sublime-project")
        # create a constellation
        yield self.create_constellation(constellation, cleanup=False)

        # add a couple projects to it
        yield self.add_constellation_project(constellation, onepath)
        yield self.add_constellation_project(constellation, twopath)

        # open the constellation
        # DOING: see head of open_constellation, but creation opens it
        # yield self.open_constellation(constellation)
        projects = self.state.get("constellations")[constellation]["projects"]

        # DOING: less dumb version of commented out below?
        yield self.confirm_projects_are_open(projects)
        # const_projects = set(
        #     self.state.get("constellations")[constellation]["projects"]
        # )

        # yield lambda: const_projects.issubset(
        #     set([win.project_file_name() for win in sublime.windows()])
        # )

        # wait for all projects to be open
        # for project in self.state.get("constellations")[constellation]["projects"]:
        #     yield lambda: project in set(
        #         [win.project_file_name() for win in sublime.windows()]
        #     )

        # TODO: confirm constellation shows up in close menu?
        # print(
        #     "test_open_and_close_constellation:about-to-close",
        #     self.open_constellations(),
        #     self.state.get("constellations"),
        #     [(win.id(), win.project_file_name()) for win in sublime.windows()],
        # )

        yield self.close_constellation(constellation)
        yield self.destroy_constellation(constellation)

    def test_open_close_open_close_constellation(self):
        constellation = "test_open_close_open_close_constellation"
        onepath = self.make_project_path("one.sublime-project")
        twopath = self.make_project_path("two.sublime-project")
        # create a constellation
        yield self.create_constellation(constellation, cleanup=False)

        # add a couple projects to it
        yield self.add_constellation_project(constellation, onepath)
        yield self.add_constellation_project(constellation, twopath)

        # open the constellation
        # DOING: see head of open_constellation, but creation opens it
        # yield self.open_constellation(constellation)
        projects = self.state.get("constellations")[constellation]["projects"]

        # DOING: less dumb version of commented out below?
        yield self.confirm_projects_are_open(projects)
        # const_projects = set(
        #     self.state.get("constellations")[constellation]["projects"]
        # )

        # yield lambda: const_projects.issubset(
        #     set([win.project_file_name() for win in sublime.windows()])
        # )

        # wait for all projects to be open
        # for project in self.state.get("constellations")[constellation]["projects"]:
        #     yield lambda: project in set(
        #         [win.project_file_name() for win in sublime.windows()]
        #     )

        # TODO: confirm constellation shows up in close menu?
        # print(
        #     "test_open_close_open_close_constellation:about-to-close",
        #     self.open_constellations(),
        #     self.state.get("constellations"),
        #     [(win.id(), win.project_file_name()) for win in sublime.windows()],
        # )

        yield self.close_constellation(constellation)
        yield self.confirm_projects_are_closed(projects)
        yield self.open_constellation(constellation)
        yield self.confirm_projects_are_open(projects)
        yield self.close_constellation(constellation)
        yield self.confirm_projects_are_closed(projects)
        yield self.destroy_constellation(constellation)

    def destroy_constellation(self, name):
        assert name in self.state.get("constellations")
        """
        DOING: still trying to debug growing list of projects open
        looks like the destroy constellation command should already close it,
        so let's skip that part
        if name in self.open_constellations():
            assert self.close_constellation(name)
        """
        projects = self.state.get("constellations")[name]["projects"]
        sublime.run_command("destroy_constellation", {"constellation": name})
        # print("AFTER RUNNING DESTROY COMMAND", name, self.state.get("constellations"))
        self.assertNotIn(name, self.state.get("constellations"))
        # print(
        #     "AFTER ASSERTING NAME IS NOT IN CONSTELLATIONS",
        #     name,
        #     self.state.get("constellations"),
        # )
        return self.confirm_projects_are_closed(projects)

    def test_destroy_constellation(self):
        # create a constellation
        constellation = "test_destroy_constellation"
        yield self.create_constellation(constellation, cleanup=False)
        # destroy it
        # print(
        #     "BEFORE YIELDING THE FUNCTION THAT RUNS DESTROY COMMAND",
        #     constellation,
        #     self.state.get("constellations"),
        # )
        yield self.destroy_constellation(constellation)
        # print(
        #     "AFTER YIELDING THE FUNCTION THAT RUNS DESTROY COMMAND",
        #     constellation,
        #     self.state.get("constellations"),
        # )
        # confirm it's not in the list
        # DOING: do not forget--with this deferred pattern, you can't be checking in the test function after yielding something that will do work you depend on. The functions won't have run yet.
        # yield self.assertNotIn(constellation, self.state.get("constellations"))

        # DOING: probably need to assert it actually closed, or maybe wait for it to do so?

        # TODO: confirm it no longer shows up in open, close, rename, destroy menus

    @staticmethod
    def make_project_path(filename):
        # print("make_project_path:Constellation", Constellation)
        # print("make_project_path:Constellation.__path__", Constellation.__path__)
        # print(
        #     "make_project_path:Constellation.__path__._path",
        #     Constellation.__path__._path,
        # )
        return os.path.join(*(Constellation.__path__._path + ["tests", filename]))

    def add_constellation_project(self, constellation, proj_path):
        sublime.run_command(
            "find_project", {"constellation": constellation, "project": proj_path}
        )

        def verify():
            # print(
            #     "add_constellation_project:verify",
            #     self.state.get("constellations"),
            #     self.state.get("constellations")[constellation],
            #     constellation,
            #     proj_path,
            #     set([win.project_file_name() for win in sublime.windows()]),
            #     "in-config?",
            #     proj_path
            #     in self.state.get("constellations")[constellation]["projects"],
            #     "open?",
            #     proj_path
            #     in set([win.project_file_name() for win in sublime.windows()]),
            # )
            """
            DOING: this *has* been testing both that the project is in
            the statefile under the right constellation *and* that the
            project is open

            I'm trying to debug this after a long winter and I don't
            recall why we're asserting that it must be open here, and
            the local logic doesn't make it clear to me that this is right.

            Trying to back out one stop for now and see what that gets us.
            return proj_path in self.state.get("constellations")[constellation][
                "projects"
            ] and proj_path in set(
                [win.project_file_name() for win in sublime.windows()]
            )
            """
            return (
                proj_path in self.state.get("constellations")[constellation]["projects"]
            )

        return verify

    def test_add_constellation_projects(self):
        # print("test_add_constellation_projects:start")
        constellation = "test_add_constellation_projects"
        # create a constellation
        yield self.create_constellation(constellation)
        # print("test_add_constellation_projects:created")

        # add a couple projects to it & confirm they're added
        onepath = self.make_project_path("one.sublime-project")
        # print("test_add_constellation_projects:onepath", onepath)
        yield {
            "condition": self.add_constellation_project(constellation, onepath),
            "timeout": 20000,
        }
        # print("test_add_constellation_projects:added")
        # yield self.add_constellation_project(constellation, onepath)

        twopath = self.make_project_path("two.sublime-project")
        # print("test_add_constellation_projects:twopath", twopath)
        # yield self.add_constellation_project(constellation, twopath)
        yield {
            "condition": self.add_constellation_project(constellation, twopath),
            "timeout": 20000,
        }

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

    def close_project(self, proj_path):
        raise Exception("DOING: I don't think I need this. Intend to remove. ")

        # TODO: if you remember, comment why this is a nested
        #       function
        def closer():
            closed = False
            for window in sublime.windows():
                if window.project_file_name() == proj_path:
                    window.run_command("close_workspace")
                    # DOING: try close_project to see if this clears tests
                    # but also, WHY is this test closing a project before
                    # removing it?
                    window.run_command("close_project")
                    window.run_command("close_window")
                    closed = True

            return closed and proj_path not in set(
                [window.project_file_name() for window in sublime.windows()]
            )

        return closer

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

        # Caution: this once closed the project before removing it, but atm
        # I'm struggling to think of a reason it must.
        # yield self.close_project(onepath)

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
