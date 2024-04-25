# -*- coding: utf-8 -*-
"""
v0.5
  - convert to API 0.5
  - temporary removed rich html support due https://github.com/albertlauncher/albert/issues/1164
v0.6
  - convert to API 2.1
"""

import json
from pathlib import Path
from shutil import which
from typing import List, Literal, Optional, Tuple
from albert import *
import sqlite3


md_name = "Visual Studio Code"
md_iid = "2.1"
md_description = "Open & search recent Visual Studio Code files and folders."
md_id = "vs"
md_version = "0.7"
md_maintainers = ["@mparati31", "@bierchermuesli"]
md_url = "https://github.com/mparati31/albert-vscode"


class Plugin(PluginInstance, GlobalQueryHandler):
    ICON = [f"file:{Path(__file__).parent}/icon.png"]
    VSCODE_RECENT_PATH = Path.home() / ".config" / "Code" / "User" / "globalStorage" / "state.vscdb"
    EXECUTABLE = which("code")
    VSCDB_HISTORY_KEY = "history.recentlyOpenedPathsList"

    def __init__(self):
        GlobalQueryHandler.__init__(self, id=md_id, name=md_name, description=md_description, defaultTrigger="vs ")
        PluginInstance.__init__(self, extensions=[self])

    # Returns the following tuple: (recent files paths, recent folders paths).
    def get_visual_studio_code_recent(
        self,
    ) -> Tuple[List[str], List[str]]:
        con = sqlite3.connect(self.VSCODE_RECENT_PATH)
        cur = con.cursor()
        res = cur.execute("SELECT value FROM ItemTable WHERE key = (?)", [self.VSCDB_HISTORY_KEY])
        result = res.fetchone()[0]
        
        storage = json.loads(result)
        menu_items = storage["entries"]

        folders = list(map(lambda item: item["folderUri"], filter(lambda item: "folderUri" in item, menu_items)))
        files = list(map(lambda item: item["fileUri"], filter(lambda item: "fileUri" in item, menu_items)))
        
        return files, folders
        
    # Returns the abbreviation of `path` that has `maxchars` character size.
    def resize_path(self, path: str | Path, maxchars: int = 45) -> str:
        filepath = Path(path)
        if len(str(filepath)) <= maxchars:
            return str(filepath)
        else:
            parts = filepath.parts
            # If the path is contains only the pathname, then it is returned as is.
            if len(parts) == 1:
                return str(filepath)
            relative_len = 0
            short_path = ""
            # Iterates on the reverse path elements and adds them until the relative
            # path exceeds `maxchars`.
            for part in reversed(parts):
                if len(part) == 0:
                    continue
                if len(".../{}/{}".format(part, short_path)) <= maxchars:
                    short_path = "/{}{}".format(part, short_path)
                    relative_len += len(part)
                else:
                    break
            return "...{}".format(short_path)

    # Return a item.
    def make_item(self, text: str, subtext: str = "", actions: List[Action] = []) -> Item:
        return StandardItem(id=md_id, iconUrls=self.ICON, text=text, subtext=subtext, actions=actions)

    # Return an item that create a new window.
    def make_new_window_item(self) -> StandardItem:
        return self.make_item(
            "New Empty Window", "Open new Visual Studio Code empty window", [Action(id=md_id, text="Open in Visual Studio Code", callable=lambda: runDetachedProcess(cmdln=[self.EXECUTABLE]))]
        )

    # Return a recent item.
    def make_recent_item(self, path: str | Path, recent_type: Literal["file", "folder"]) -> Item:
        finalPath = path.replace("file://", "")
        return self.make_item(
            finalPath,
            "Open Recent {}".format(recent_type),
            [
                Action(
                    id=path,
                    text="Open in Visual Studio Code",
                    callable=lambda: runDetachedProcess(cmdln=[self.EXECUTABLE, finalPath])
                )
            ]
        )

    def handleTriggerQuery(self, query) -> Optional[List[Item]]:
        if not self.EXECUTABLE:
            return query.add(self.make_item("Visual Studio Code not installed"))

        query_text = query.string

        # debug("query: '{}'".format(query_text))

        query_text = query_text.strip().lower()
        files, folders = self.get_visual_studio_code_recent()

        # print("vs recent files: {}".format(files))
        # print("vs recent folders: {}".format(folders))

        if not folders and not files:
            return [query.add(self.make_new_window_item()), query.add(self.make_item("Recent Files and Folders not found"))]

        items = []
        for element_name in ["New Empty Window"] + folders + files:
            if query_text not in element_name.lower():
                continue
            if element_name == "New Empty Window":
                item = query.add(self.make_new_window_item())
            else:
                item = query.add(self.make_recent_item(element_name, "folder" if element_name in folders else "file"))
            items.append(item)

        return items
