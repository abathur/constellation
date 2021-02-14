import sublime
import sublime_plugin
import subprocess
import os

from .api import API


class InputConstellationName(sublime_plugin.TextInputHandler):
    initial = None
    callme = None

    def __init__(self, initial=None, name=None):
        self.initial = initial
        self.callme = name
        return super().__init__()

    def placeholder(self):
        return "Name this constellation"

    def name(self):
        return self.callme if self.callme else "name"


class SelectConstellationList(sublime_plugin.ListInputHandler, API):
    _generator = lambda self: self.constellations

    def placeholder(self):
        return "Select a Constellation"

    def name(self):
        return "constellation"

    def list_items(self):
        return list(self._generator())


class SelectClosedConstellationList(SelectConstellationList):
    _generator = lambda self: self.closed_constellations()


class SelectOpenConstellationList(SelectConstellationList):
    _generator = lambda self: self.open_constellations()


class SelectActiveConstellationList(SelectConstellationList):
    _generator = lambda self: self.active_constellations()


class BaseProjectList(sublime_plugin.ListInputHandler, API):
    def placeholder(self):
        return "Select a .sublime-project"

    def name(self):
        return "project"


class OpenProjectList(BaseProjectList):
    exclude = []

    def __init__(self, exclude=None):
        self.exclude = exclude or []
        super().__init__()

    def list_items(self):
        projects = [
            x.extract_variables() for x in sublime.windows() if x.project_file_name()
        ]
        return list(
            set(
                [
                    (x["project_name"], x["project"])
                    for x in projects
                    if x["project"] not in self.exclude
                ]
            )
        )


class ExplicitProjectList(BaseProjectList):
    projects = []

    def __init__(self, projects):
        self.projects = projects or []
        super().__init__()

    def list_items(self):
        return list(set([(x.split("/")[-1], x) for x in self.projects]))


# TODO: for now, we're assuming the user is smart enough to figure out if there's a workspace/project pair here, but ideally we should check.


class UpgradeWorkspaceList(sublime_plugin.ListInputHandler, API):
    def list_items(self, *args):
        cmd = "find {:} -maxdepth 5 -name '*.sublime-workspace'".format(
            self.search_path
        )
        workspaces = set()
        for path in subprocess.check_output(
            cmd, shell=True, universal_newlines=True
        ).splitlines():
            if not os.path.exists(
                path.replace(".sublime-workspace", ".sublime-project")
            ):
                workspaces.add((path.replace(self.search_path, ".."), path))

        return sorted(list(workspaces))

    def placeholder(self):
        return "Select a .sublime-workspace"

    def name(self):
        return "workspace_path"


class SearchProjectList(OpenProjectList):
    def list_items(self, *args):
        cmd = "find {:} -maxdepth 5 -name '*.sublime-project'".format(self.search_path)
        projects = set()

        for path in subprocess.check_output(
            cmd, shell=True, universal_newlines=True
        ).splitlines():
            if path not in self.exclude:
                projects.add((path.replace(self.search_path, ".."), path))

        return sorted(list(projects))

    def placeholder(self):
        return "Select a .sublime-project"

    def name(self):
        return "project"


class RenameList(SelectActiveConstellationList):
    def next_input(self, args):  # args is inexplicably a kwarg dict
        return InputConstellationName(name="new_name")


class ProjectList(SelectActiveConstellationList):
    def next_input(self, args):
        return OpenProjectList(self.constellations[args["constellation"]]["projects"])


class ConstellationProjectList(SelectActiveConstellationList):
    def next_input(self, args):
        return ExplicitProjectList(
            self.constellations[args["constellation"]]["projects"]
        )


class FoundWorkspaceList(SelectConstellationList):
    def next_input(self, *args):
        return UpgradeWorkspaceList()


class FoundProjectList(SelectConstellationList):
    def next_input(self, args):
        return SearchProjectList(self.constellations[args["constellation"]]["projects"])
