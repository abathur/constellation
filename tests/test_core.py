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

        # clean up
        self.destroy_constellation(constellation)

    def open_constellation(self, name):
        sublime.run_command("open_constellation", {"constellation": name})
        return lambda: name in self.open_constellations()

    def close_constellation(self, name):
        sublime.run_command("close_constellation", {"constellation": name})
        return lambda: name not in self.open_constellations()

    def test_open_and_close_constellation(self):
        constellation = "test_open_and_close_constellation"
        onepath = self.make_project_path("one.sublime-project")
        twopath = self.make_project_path("two.sublime-project")
        # create a constellation
        yield self.create_constellation(constellation)

        # add a couple projects to it
        yield self.add_constellation_project(constellation, onepath)
        yield self.add_constellation_project(constellation, twopath)

        # open the constellation
        yield self.open_constellation(constellation)

        # wait for all projects to be open
        for project in self.state.get("constellations")[constellation]["projects"]:
            yield lambda: project in set(
                [win.project_file_name() for win in sublime.windows()]
            )

        # TODO: confirm constellation shows up in close menu?

        yield self.close_constellation(constellation)

    def destroy_constellation(self, name):
        sublime.run_command("destroy_constellation", {"constellation": name})
        return lambda: name not in self.state.get("constellations")

    def test_destroy_constellation(self):
        # create a constellation
        constellation = "test_destroy_constellation"
        yield self.create_constellation(constellation, cleanup=False)

        # destroy it
        yield self.destroy_constellation(constellation)

        # confirm it's not in the list
        self.assertNotIn(constellation, self.state.get("constellations"))

        # TODO: confirm it no longer shows up in open, close, rename, destroy menus

    @staticmethod
    def make_project_path(filename):
        return os.path.join(*(Constellation.__path__._path + ["tests", filename]))

    def add_constellation_project(self, constellation, proj_path):
        sublime.run_command(
            "add_project", {"constellation": constellation, "project": proj_path}
        )
        return (
            lambda: proj_path
            in self.state.get("constellations")[constellation]["projects"]
        )

    def test_add_constellation_projects(self):
        constellation = "test_add_constellation_projects"
        # create a constellation
        yield self.create_constellation(constellation)

        # add a couple projects to it & confirm they're added
        onepath = self.make_project_path("one.sublime-project")
        yield self.add_constellation_project(constellation, onepath)

        twopath = self.make_project_path("two.sublime-project")
        yield self.add_constellation_project(constellation, twopath)

        self.remove_project_menu_contains(
            constellation,
            [("one.sublime-project", "wrongboy"), ("two.sublime-project", "rightboy"),],
        )

        # clean up
        self.destroy_constellation(constellation)

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

        # rm and confirm it's not in list
        yield self.remove_constellation_project(constellation, onepath)

        # TODO: confirm it no longer appears in the remove menu?

        # clean up
        self.destroy_constellation(constellation)

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
