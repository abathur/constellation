"""
TODO: I'm really starting to chafe at the organization of this, but I don't have time to break it up right now.

See Randy3k's example of yielding lambdas during setup?
https://github.com/SublimeText/UnitTesting/blob/master/unittesting/helpers/temp_directory_test_case.py

I wonder if pytest is compatible with deferrabletestcase
"""

import sublime
import os

from unittesting import DeferrableTestCase
import Constellation
from Constellation import input_handlers


class TestCore(DeferrableTestCase):
    state = None

    def setUp(self):
        Constellation.api.API.load_state()
        self.state = Constellation.api.API.state

    def tearDown(self):
        try:
            self.destroy_constellation("test_one")
        # some tests close it on their own...
        except KeyError:
            pass

    def create_constellation(self, name):
        sublime.run_command("create_constellation", {"name": name})
        return 1000  # delay to give ST3 time to work

    def test_create_constellation(self):
        yield self.create_constellation("test_one")
        # confirm the constellation record exists
        self.assertIn("test_one", self.state.get("constellations"))

        # TODO: confirm it shows up in the open, destroy, and rename menus

    def open_constellation(self, name):
        sublime.run_command("open_constellation", {"constellation": name})
        return 1000  # delay to give ST3 time to work

    def close_constellation(self, name):
        sublime.run_command("close_constellation", {"constellation": name})
        return 1000  # delay to give ST3 time to work

    def test_open_and_close_constellation(self):
        constellation = "test_one"
        onepath = self.make_project_path("one.sublime-project")
        twopath = self.make_project_path("two.sublime-project")
        # create a constellation
        yield self.create_constellation(constellation)

        # add a couple projects to it
        yield self.add_constellation_project(constellation, onepath)
        yield self.add_constellation_project(constellation, twopath)

        # open the constellation
        yield self.open_constellation(constellation)

        # confirm the projects are open
        open_projects = set([win.project_file_name() for win in sublime.windows()])
        for project in self.state.get("constellations")[constellation]["projects"]:
            yield 100
            self.assertIn(project, open_projects)

        # confirm constellation marked open
        self.assertTrue(self.state.get("constellations")[constellation]["open"])
        yield 100

        # TODO: confirm constellation shows up in close menu

        yield self.close_constellation(constellation)

        # confirm the projects are closed
        open_projects = set([win.project_file_name() for win in sublime.windows()])
        for project in self.state.get("constellations")[constellation]["projects"]:
            self.assertNotIn(project, open_projects)

        # confirm const is marked closed
        self.assertFalse(self.state.get("constellations")[constellation]["open"])

    def destroy_constellation(self, name):
        sublime.run_command("destroy_constellation", {"constellation": name})
        return 1000  # delay to give ST3 time to work

    def test_destroy_constellation(self):
        # create a constellation
        constellation = "test_one"
        yield self.create_constellation(constellation)

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
        return 1000  # delay to give ST3 time to work

    def test_add_constellation_projects(self):
        constellation = "test_one"
        # create a constellation
        yield self.create_constellation(constellation)

        # add a couple projects to it
        onepath = self.make_project_path("one.sublime-project")
        yield self.add_constellation_project(constellation, onepath)

        # confirm it is added
        self.assertIn(
            onepath, self.state.get("constellations")[constellation]["projects"]
        )

        twopath = self.make_project_path("two.sublime-project")
        yield self.add_constellation_project(constellation, twopath)

        self.assertIn(
            twopath, self.state.get("constellations")[constellation]["projects"]
        )
        yield 100

        self.remove_project_menu_contains(
            "test_one",
            [("one.sublime-project", "wrongboy"), ("two.sublime-project", "rightboy"),],
        )

    def remove_constellation_project(self, constellation, proj_path):
        sublime.run_command(
            "remove_project", {"constellation": constellation, "project": proj_path}
        )
        return 1000  # delay to give ST3 time to work

    def test_remove_constellation_project(self):
        constellation = "test_one"
        onepath = self.make_project_path("one.sublime-project")
        # create a constellation
        yield self.create_constellation(constellation)

        self.assertNotIn(
            onepath, self.state.get("constellations")[constellation]["projects"]
        )
        yield 100
        # add a couple projects to it

        yield self.add_constellation_project(constellation, onepath)

        self.assertIn(
            onepath, self.state.get("constellations")[constellation]["projects"]
        )
        yield 100

        yield self.remove_constellation_project(constellation, onepath)

        # confirm it is removed
        self.assertNotIn(
            onepath, self.state.get("constellations")[constellation]["projects"]
        )

        # TODO: confirm it no longer appears in the remove menu
        yield 100

    def remove_project_menu(self, constellation):
        handle = input_handlers.ConstellationProjectList()
        return handle.next_input({"constellation": constellation}).list_items()

    def remove_project_menu_contains(self, constellation, projects):
        # make sure the remove menu has the right projects:
        self.assertEqual(
            set(self.remove_project_menu("test_one")),
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
