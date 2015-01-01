import re
import sublime
import sublime_plugin
from .filter import PromptFilterToLinesCommand


class PromptFoldToLinesCommand(PromptFilterToLinesCommand):

    def run(self, search_type = 'string'):
        self._run(search_type, "fold_to_lines", "Fold")

    def prompt_for_custom_separator(self):
        pass

    def on_separator(self, separator):
        pass


class FoldToLinesCommand(sublime_plugin.TextCommand):

    def run(self, edit, needle, search_type):
        settings = sublime.load_settings(settings_path)
        self.needle = needle
        self.search_type = search_type
        self.case_sensitive = False
        if search_type == 'string':
            self.case_sensitive = settings.get('case_sensitive_string_search', False)
        elif search_type == 'regex':
            self.case_sensitive = settings.get('case_sensitive_regex_search', True)
        self.invert_search = settings.get('invert_search', False)
        if search_type == 'string':
            self.match_pattern = re.compile(re.escape(self.needle), 0 if self.case_sensitive else re.IGNORECASE)
        else:
            self.match_pattern = re.compile(self.needle, 0 if self.case_sensitive else re.IGNORECASE)
        self.fold(edit)

    def fold(self, edit):
        regions = [ sublime.Region(0, self.view.size()) ]
        for region in reversed(regions):
            lines = self.view.split_by_newlines(region)
            folds = []
            for line in reversed(lines):
                matched = bool(self.match_pattern.search(self.view.substr(line))) ^ self.invert_search
                if matched and folds:
                    self.fold_regions(folds)
                    folds = []
                elif not matched:
                    folds.append(line)
            if folds:
                self.fold_regions(folds)

    def fold_regions(self, folds):
        region = sublime.Region(folds[0].end(), folds[0].end())
        for fold in folds:
            region = region.cover(fold)
        self.view.fold(region)
