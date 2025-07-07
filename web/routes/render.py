from dataclasses import dataclass


@dataclass
class BreadcrumbsItem:
    name: str
    url: str = None
