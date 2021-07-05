import os
import re
from typing import Match

from mkdocs.utils import meta as meta_util, get_markdown_title

from .types import EzLinksOptions, BrokenLink
from .scanners.base_link_scanner import BaseLinkScanner
from .file_mapper import FileMapper


class EzLinksReplacer:
    def __init__(
            self,
            root: str,
            file_map: FileMapper,
            use_directory_urls: bool,
            options: EzLinksOptions,
            logger):
        self.root = root
        self.file_map = file_map
        self.use_directory_urls = use_directory_urls
        self.options = options
        self.scanners = []
        self.logger = logger
        self.config = []

    def get_meta(self, path):
        try:
            with open(path, 'r', encoding='utf-8-sig', errors='strict') as f:
                source = f.read()
                meta = meta_util.get_data(source)
                return meta[1] if meta else None
        except OSError as e:
            print(e)
            return None

    def add_scanner(self, scanner: BaseLinkScanner) -> None:
        self.scanners.append(scanner)

    def replace(self, path: str, markdown: str, config) -> str:
        self.path = path
        self.config = config

        # Multi-Pattern search pattern, to capture  all link types at once
        return re.sub(self.regex, self._do_replace, markdown)

    # Compiles all scanner patterns as a multi-pattern search, with
    # built in code fence skipping (individual link scanners don't
    # have to worry about them.
    def compile(self):
        patterns = '|'.join([scanner.pattern() for scanner in self.scanners])
        self.regex = re.compile(
            fr'''
            (?: # Attempt to match a code block
                [`]{{3}}
                (?:[\w\W]*?)
                [`]{{3}}$
            | # Match an inline code block
                `[\w\W]*?`
            )
            | # Attempt to match any one of the subpatterns
            (?:
                {patterns}
            )
            ''', re.X | re.MULTILINE)

    def _do_replace(self, match: Match) -> str:
        abs_from = os.path.dirname(os.path.join(self.root, self.path))

        try:
            for scanner in self.scanners:
                if scanner.match(match):
                    link = scanner.extract(match)

                    # Do some massaging of the extracted results
                    if not link:
                        raise BrokenLink(f"Could not extract link from '{match.group(0)}'")

                    # Handle case of local page anchor
                    if not link.target:
                        if link.anchor:
                            link.target = os.path.join(self.root, self.path)
                        else:
                            raise BrokenLink(f"No target for link '{match.group(0)}'")
                    else:
                        # Otherwise, search for the target through the file map
                        search_result = self.file_map.search(self.path, link.target)
                        if not self.use_directory_urls:
                            search_result = search_result + '.md' if '.' not in search_result else search_result

                        if search_result:
                            path = os.path.join(self.config['docs_dir'], link.target)
                            meta = self.get_meta(search_result)
                            if meta:
                                if not link.text and meta.get('title'):
                                    link.text = meta.get('title')
                                if 'icon-only' in link.style:
                                    link.title = meta.get('title')
                                elif not link.title and meta.get('summary'):
                                    link.title = meta.get('summary')
                                if meta.get('icon'):
                                    link.icon = meta.get('icon').replace('/', '-')
                            else:
                                link.text = link.target
                        else:
                            link.src_not_found = True
                            raise BrokenLink(f"'{link.target}' not found.")

                        link.target = search_result

                    if self.options.wiki_html_class:
                        link.class_name = self.options.wiki_html_class

                    link.target = os.path.relpath(link.target, abs_from)
                    return link.render()
        except BrokenLink as ex:
            # Log these out as Debug messages, as the regular mkdocs
            # strict mode will log out broken links.
            self.logger.debug(f"[EzLinks] {ex}")

        # Fall through, return the original link unaltered, and let mkdocs handle it
        return match.group(0)
