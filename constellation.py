"""
Collect ST3 projects/workspaces into "Constellations"

When you open or close a constellation, it opens or closes all of the included projects.
"""

import sublime
import sublime_plugin

import os
import subprocess
import json

from .util import input_handlers as collect
from .util.api import API
from .util import constants as c


def plugin_loaded():
    API.load_state()


def plugin_unloaded():
    API.save_state()


class _BaseApplicationCommand(sublime_plugin.ApplicationCommand, API):
    pass


# TODO: I won't pretend to completely grok when and why ST3's api uses the various arg-passing conventions it's using. May be worth a refactor when this is better understood.


class OpenConstellationsInfoCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Open Constellations: {:}/{:}".format(
            len(self._open_constellations), len(self.active_constellations())
        )


# TODO: can remove below when a pure python or Windows-safe fallback for 'find' is implemented
class WindowsUserQuestionCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Help wanted (see github) on these:"


class OpenConstellationsCommand(_BaseApplicationCommand):
    def is_visible(self, index=None, **args):
        return index < len(self._open_constellations)

    def is_enabled(self, index=None, **args):
        return True

    def description(self, index=None, **args):
        const = relevant = None
        if index < len(self._open_constellations):
            relevant = self.open_constellations()
            const = relevant[index]
        return (
            "    {} [{}]".format(
                const, "∗" * len(self.constellations[const]["projects"])
            )
            if index < len(relevant)
            else "Oops. You shouldn't be seeing this. Better find someone who works here."
        )

    def run(self, index=None, **args):
        if index < len(self._open_constellations):
            relevant = self.open_constellations()
            const = relevant[index]
            return CloseConstellationCommand().run(const)


class _ExistingConstellationCommand(_BaseApplicationCommand):
    _list_class = collect.SelectConstellationList

    def input(self, constellation):
        return self._list_class()

    def is_enabled(self, constellation=None, **kwargs):
        return True if len(self._list_class._generator(self)) else False


class _OpenConstellationCommand(_ExistingConstellationCommand):
    _list_class = collect.SelectOpenConstellationList


class _ClosedConstellationCommand(_ExistingConstellationCommand):
    _list_class = collect.SelectClosedConstellationList


class _ActiveConstellationCommand(_ExistingConstellationCommand):
    _list_class = collect.SelectActiveConstellationList


class ManageConstellationsInfoCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Constellations"


class CreateConstellationCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.InputConstellationName()

    def run(self, name):
        self.add_constellation(name)
        self.open_constellation(name)


class CreateConstellationFromOpenProjectCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.OpenProjectList(exclude=self.projects_in_constellations())

    def run(self, project):
        name = os.path.splitext(os.path.basename(project))[0]
        self.add_constellation(name)
        self.open_constellation(name)
        # add project to eponymous constellation
        self.add_to(name, project, already_open=True)


class CreateConstellationFromProjectFileCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.SearchProjectList()

    def run(self, project):
        name = os.path.splitext(os.path.basename(project))[0]
        self.add_constellation(name)
        self.open_constellation(name)
        # add project to eponymous constellation
        self.add_to(name, project)


class CreateConstellationFromWorkspaceFileCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.UpgradeWorkspaceList()

    def run(self, project):
        name = os.path.splitext(os.path.basename(project))[0]
        self.add_constellation(name)
        self.open_constellation(name)
        # add project to eponymous constellation
        self.add_to(name, project)


class DestroyConstellationCommand(_ActiveConstellationCommand):
    def run(self, constellation):
        if constellation not in self.constellations:
            return

        if constellation in self._open_constellations:
            self.close_constellation(constellation)

        self.remove_constellation(constellation)


class RenameConstellationCommand(_ActiveConstellationCommand):
    def input(self, args):
        return collect.RenameList()

    def run(self, constellation, new_name):
        if constellation not in self.constellations:
            return
        self.rename_constellation(constellation, new_name)


class OpenConstellationCommand(_ClosedConstellationCommand):
    def run(self, constellation):
        self.open_constellation(constellation)


class CloseConstellationCommand(_OpenConstellationCommand):
    def run(self, constellation):
        if constellation not in self._open_constellations:
            return

        for project in self.projects_for(constellation):
            for window in sublime.windows():
                if window.project_file_name() == project:
                    window.run_command("close_workspace")
                    if window.id() != sublime.active_window().id():
                        window.run_command("close_window")
        self.close_constellation(constellation)


class ManageProjectsInfoCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Constellation Projects"


class AddProjectCommand(_ActiveConstellationCommand):
    already_open = True

    def input(self, args):
        return collect.ProjectList()

    def run(self, constellation, project):
        self.add_to(constellation, project, already_open=self.already_open)


# We have opinions, and one of those is that workspaces are annoying to work with directly. Because of this opinion, the only way we're going to support working with them is by explicitly upgrading it to a project (but then replacing the project file with a link back to whatever project the workspace was in) so you get the benefits of having a workspace, but we don't have to have arcane methods of working with them.


class UpgradeWorkspaceCommand(AddProjectCommand):
    already_open = False

    def is_enabled(self, *args):
        # TODO: remove below when there's a fallback
        if sublime.platform() == "windows":
            return False
        search_root = self.search_path
        return (
            True
            if search_root and len(search_root) and os.path.exists(search_root)
            else False
        )

    def input(self, args):
        return collect.FoundWorkspaceList()

    def run(self, constellation, workspace_path):
        if not workspace_path:
            # print(c.LOG_TEMPLATE, "Nothing found to upgrade")
            return

        workspace = None

        # load the workspace
        with open(workspace_path, "r") as infile:
            workspace = json.load(infile)

        project = os.path.join(os.path.dirname(workspace_path), workspace["project"])
        workspace_project = workspace_path.replace(
            ".sublime-workspace", ".sublime-project"
        )

        if len(workspace["project"]) and os.path.exists(project):
            # this seems to be set to a real value, so we'll make a link to the sublime-project
            subprocess.Popen(
                "ln -f '{:}' '{:}'".format(project, workspace_project), shell=True
            )
        elif not os.path.exists(workspace_project):
            # some projects might have a null value, or maybe the file got deleted, so we'll just make an empty project
            with open(workspace_project, "w") as outfile:
                json.dump({}, outfile, indent=1)
        else:
            pass
            # print(
            #     c.LOG_TEMPLATE,
            #     "I really hope we never get here",
            #     workspace,
            #     workspace_project,
            #     workspace_path,
            #     project,
            # )

        workspace["project"] = workspace_project

        with open(workspace_path, "w") as outfile:
            json.dump(workspace, outfile, indent=1)

        super().run(constellation, workspace_project)

        # at this point, we need to have taken the workspace file, added a link adjacent to the project file, and replaced the project key in the workspace file with the pointer to the adjacent file


class FindProjectCommand(AddProjectCommand):
    already_open = False

    def is_enabled(self, *args):
        # TODO: remove below when there's a fallback
        if sublime.platform() == "windows":
            return False
        search_root = self.search_path
        return (
            True
            if search_root and len(search_root) and os.path.exists(search_root)
            else False
        )

    def input(self, args):
        return collect.FoundProjectList()


class RemoveProjectCommand(_ActiveConstellationCommand):
    def input(self, args):
        return collect.ConstellationProjectList()

    def run(self, constellation, project):
        self.remove_from(constellation, project)
