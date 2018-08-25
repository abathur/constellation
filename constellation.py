"""
Collect ST3 projects/workspaces into "Constellations"

When you open or close a constellation, it opens or closes all of the included projects.
"""

import sublime
import sublime_plugin

import os
import subprocess
import json

from .subl import subl
from . import input_handlers as collect
from .api import API
from . import constants as c


def plugin_loaded():
    API.load_state()


def plugin_unloaded():
    API.save_state()


class _BaseApplicationCommand(sublime_plugin.ApplicationCommand, API):
    pass


# TODO: I won't pretend to completely grok when and why ST3's api uses the various arg-passing conventions it's using. May be worth a refactor when this is better understood.

class InfoCommand(_BaseApplicationCommand):

    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Open Constellations: {:}/{:}".format(
            len(self.open_constellations), len(self.active_constellations)
        )

# TODO: can remove below when a pure python or Windows-safe fallback for 'find' is implemented
class WindowsUserQuestionCommand(_BaseApplicationCommand):

    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Help wanted (see github) on these:"


class OpenConstellationsCommand(_BaseApplicationCommand):

    def is_visible(self, index=None, **args):
        return index < len(self.open_constellations)

    def is_enabled(self, index=None, **args):
        return False

    def description(self, index=None, **args):
        const = None
        if index < len(self.open_constellations):
            const = self.open_constellations[index]
        return "    {} [{}]".format(
            const, "∗" * len(self.constellations[const]["projects"])
        ) if index < len(
            self.open_constellations
        ) else "Oops. You shouldn't be seeing this. Better find someone who works here."


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


class CreateConstellationCommand(_BaseApplicationCommand):

    def input(self, args):
        return collect.InputConstellationName()

    def run(self, name):
        self.add_constellation(name)


class DestroyConstellationCommand(_ActiveConstellationCommand):

    def run(self, constellation):
        self.remove_constellation(constellation)


class RenameConstellationCommand(_ActiveConstellationCommand):

    def input(self, args):
        return collect.RenameList()

    def run(self, constellation, new_name):
        self.rename_constellation(constellation, new_name)


class OpenConstellationCommand(_ClosedConstellationCommand):

    def run(self, constellation):
        self.open_constellation(constellation)

        for project in self.projects_for(constellation):
            subl("-n", project)


class CloseConstellationCommand(_OpenConstellationCommand):

    def run(self, constellation):
        for project in self.projects_for(constellation):
            for window in sublime.windows():
                if window.project_file_name() == project:
                    window.run_command("close_workspace")
                    if window.id() != sublime.active_window().id():
                        window.run_command("close_window")

        self.close_constellation(constellation)


class AddProjectCommand(_ActiveConstellationCommand):

    def input(self, args):
        return collect.ProjectList()

    def run(self, constellation, project):
        self.add_to(constellation, project)


# We have opinions, and one of those is that workspaces are annoying to work with directly. Because of this opinion, the only way we're going to support working with them is by explicitly upgrading it to a project (but then replacing the project file with a link back to whatever project the workspace was in) so you get the benefits of having a workspace, but we don't have to have arcane methods of working with them.


class UpgradeWorkspaceCommand(AddProjectCommand):

    def is_enabled(self, *args):
        # TODO: remove below when there's a fallback
        if sublime.platform() == "windows":
            return False
        search_root = self.search_path
        return True if search_root and len(search_root) and os.path.exists(
            search_root
        ) else False

    def input(self, args):
        return collect.FoundWorkspaceList()

    def run(self, constellation, workspace_path):
        if not workspace_path:
            #print(c.LOG_TEMPLATE, "Nothing found to upgrade")
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

        if self.constellations[constellation]["open"]:
            subl("-n", project)


class FindProjectCommand(AddProjectCommand):

    def is_enabled(self, *args):
        # TODO: remove below when there's a fallback
        if sublime.platform() == "windows":
            return False
        search_root = self.search_path
        return True if search_root and len(search_root) and os.path.exists(
            search_root
        ) else False

    def input(self, args):
        return collect.FoundProjectList()

    def run(self, constellation, project):
        super().run(constellation, project)

        if self.constellations[constellation]["open"]:
            subl("-n", project)


class RemoveProjectCommand(_ActiveConstellationCommand):

    def input(self, args):
        return collect.ConstellationProjectList()

    def run(self, constellation, project):
        super().run(constellation, project)
        self.remove_from(constellation, project)
