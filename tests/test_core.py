import sublime
import os

from unittesting import DeferrableTestCase
import Constellation


class TestCore(DeferrableTestCase):

    def create_constellation(self, name):
        sublime.run_command("create_constellation", {"name": name})
        yield 1000

        # confirm the constellation record exists
        s = sublime.load_settings("Constellation.sublime-settings")
        self.assertIn(name, s.get("constellations"))

    def open_constellation(self, name):
        sublime.run_command("open_constellation", {"constellation": name})
        yield 1000

        # confirm the projects are open
        s = sublime.load_settings("Constellation.sublime-settings")
        open_projects = set([win.project_file_name() for win in sublime.windows()])
        for project in s.get("constellations")[name]["projects"]:
            self.assertIn(project, open_projects)

        # confirm constellation marked open
        self.assertTrue(s.get("constellations")[name]["open"])

    def close_constellation(self, name):
        sublime.run_command("close_constellation", {"constellation": name})
        yield 1000

        # confirm the projects are closed
        s = sublime.load_settings("Constellation.sublime-settings")
        open_projects = set([win.project_file_name() for win in sublime.windows()])
        for project in s.get("constellations")[name]["projects"]:
            self.assertNotIn(project, open_projects)

        # confirm const is marked closed
        self.assertFalse(s.get("constellations")[name]["open"])

    def destroy_constellation(self, name):
        sublime.run_command("destroy_constellation", {"constellation": name})

        # confirm constellation record is gone
        s = sublime.load_settings("Constellation.sublime-settings")
        self.assertNotIn(name, s.get("constellations"))

    def add_constellation_project(self, constellation, project_filename):

        project_path = os.path.join(
            *(Constellation.__path__._path + ["tests", project_filename])
        )

        sublime.run_command(
            "add_project", {"constellation": constellation, "project": project_path}
        )
        # confirm it is added
        s = sublime.load_settings("Constellation.sublime-settings")
        self.assertIn(project_path, s.get("constellations")[constellation]["projects"])

    def remove_constellation_project(self, constellation, project_filename):
        project_path = os.path.join(
            *(Constellation.__path__._path + ["tests", project_filename])
        )

        sublime.run_command(
            "remove_project", {"constellation": constellation, "project": project_path}
        )
        # confirm it is removed
        s = sublime.load_settings("Constellation.sublime-settings")
        self.assertNotIn(
            project_path, s.get("constellations")[constellation]["projects"]
        )

    # TODO: not sure how well this actually exercises input handlers, though coverage claims to be at 56%; may not be fair to claim core is tested if we aren't confirming the correct items are showing up in menus?

    def test_core_commands(self):
        # create a constellation
        self.create_constellation("test_one")

        # add a couple projects to it
        self.add_constellation_project("test_one", "one.sublime-project")
        self.add_constellation_project("test_one", "two.sublime-project")

        # open the constellation
        self.open_constellation("test_one")

        # remove a project from the constellation
        self.remove_constellation_project("test_one", "two.sublime-project")

        # remove the constellation
        self.destroy_constellation("test_one")
