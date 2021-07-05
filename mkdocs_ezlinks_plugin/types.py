from dataclasses import dataclass


class BrokenLink(Exception):
    pass

@dataclass
class Link:
    ''' Dataclass to hold the contents required to form a complete Link. '''
    image: bool
    text: str
    target: str
    anchor: str
    title: str
    style: str
    icon: str

    # Render as a complete MD compatible link
    def render(self):
        img = '!' if self.image else ''
        anchor = f"#{self.anchor}" if self.anchor else ''
        title = f' "{self.title}"' if self.title else ''
        text = f'{self.text}' if self.text else ''
        class_name = f'.{self.class_name}' if self.class_name else ''
        icon = f':{self.icon}: ' if self.icon else ''

        return f"{img}[{icon}{self.text}]({self.target}{anchor}{title}){{:{self.style} {class_name}}}"


@dataclass
class EzLinksOptions:
    ''' Dataclass to hold typed options from the configuration. '''
    wikilinks: bool
    wiki_html_class: str
    warn_ambiguities: bool
