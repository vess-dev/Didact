"""Campaign state files (`<campaign>/state/<name>.yaml`): decks, bags, table memory, ….

Written through changesets like everything else, so every change is logged and undoable.
Without an active campaign, state lives with the world (`<world>/state/`).
"""

from pathlib import Path

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.repo import Repo


def state_path(repo: Repo, name: str) -> Path:
    campaign = repo.active_campaign()
    if campaign is not None:
        return repo.layout.campaign_dir(campaign.world, campaign.id) / "state" / f"{name}.yaml"
    world = repo.active_world()
    if world is None:
        raise InvalidError(
            _("state needs a world or campaign"), hint=_("`didact world new <id>` first")
        )
    return repo.layout.world_dir(world.id) / "state" / f"{name}.yaml"


def load(repo: Repo, name: str) -> dict[str, JSON]:
    path = state_path(repo, name)
    text = repo.read_text(path)
    if not text:
        return {}
    data = frontmatter.to_plain(frontmatter.load(text, where=repo.layout.rel(path)))
    return data if isinstance(data, dict) else {}


def plan(cs: Changeset, name: str, data: dict[str, JSON]) -> None:
    path = state_path(cs.repo, name)
    cs.write(path, frontmatter.dump(frontmatter.from_plain(data)))
