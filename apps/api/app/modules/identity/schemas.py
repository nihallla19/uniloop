import re
import uuid
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

HEX = r"^#[0-9A-Fa-f]{6}$"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean(value: str) -> str:
    return _CONTROL.sub("", value).strip()


CleanText = Annotated[str, AfterValidator(_clean)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RequestCodeIn(Strict):
    email: str = Field(max_length=254)
    turnstile_token: str = Field(default="", max_length=2048)


class VerifyCodeIn(Strict):
    email: str = Field(max_length=254)
    code: str = Field(pattern=r"^\d{6}$")
    # Required only on first sign-in (spec 7.1).
    display_name: CleanText | None = Field(default=None, min_length=1, max_length=50)
    accept_terms: bool = False
    confirm_age: bool = False


class ProfilePatch(Strict):
    handle: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_]{3,24}$")
    display_name: CleanText | None = Field(default=None, min_length=1, max_length=50)
    tagline: CleanText | None = Field(default=None, max_length=80)
    bio: CleanText | None = Field(default=None, max_length=300)
    accent_hex: str | None = Field(default=None, pattern=HEX)
    layout: Literal["grid", "list"] | None = None
    show_sold: bool | None = None


HomeSectionId = Literal["categories", "new", "free", "saved"]


class HomeSection(Strict):
    id: HomeSectionId
    visible: bool = True


def _default_sections() -> list[HomeSection]:
    return [HomeSection(id=s) for s in ("categories", "new", "free", "saved")]


class Preferences(Strict):
    """Private appearance settings (spec 2.3). Stored in identity.preferences.settings."""

    theme: Literal["system", "light", "dark"] = "system"
    accent: str = Field(default="#2a555c", pattern=HEX)
    glass: Literal["off", "subtle", "standard", "strong"] = "standard"
    density: Literal["comfortable", "compact"] = "comfortable"
    feed_layout: Literal["grid", "list"] = "grid"
    card_size: Literal["small", "medium", "large"] = "medium"
    text_size: Literal[90, 100, 110, 125] = 100
    motion: Literal["system", "reduced", "full"] = "system"
    default_sort: Literal["newest", "price_asc", "price_desc"] = "newest"
    hidden_categories: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    home_sections: list[HomeSection] = Field(default_factory=_default_sections, max_length=4)

    @field_validator("home_sections")
    @classmethod
    def _unique_sections(cls, v: list[HomeSection]) -> list[HomeSection]:
        if len({s.id for s in v}) != len(v):
            raise ValueError("Each home section can appear once.")
        return v
