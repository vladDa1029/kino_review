"""Branded HTML rendering for notification emails.

The markup mirrors the KinoFlow frontend look (dark navy canvas, orange accent,
Space Grotesk headings, pill buttons) while staying email-client safe: table
layout, inline styles, literal colors, and an Outlook (VML) button fallback.
"""

from datetime import datetime
from html import escape

# Palette taken from the frontend design tokens (App.css :root).
BG = "#080b12"
BG_SECONDARY = "#0d1320"
SURFACE = "#111a28"
SURFACE_STRONG = "#151f2f"
TEXT = "#f4f7fb"
TEXT_MUTED = "#a8b4c8"
LINE = "rgba(255,255,255,0.10)"
ACCENT = "#ff8a2a"
ACCENT_STRONG = "#ff6f1a"

BODY_FONT = "'Manrope','Segoe UI',Helvetica,Arial,sans-serif"
HEAD_FONT = "'Space Grotesk','Segoe UI',Helvetica,Arial,sans-serif"

_BRAND_NAME = "KinoFlow"


def render_email_html(template: str, payload: dict[str, str | None]) -> str:
    if template == "reservation_confirmation":
        return _reservation_confirmation(payload)
    if template == "project_member_invitation":
        return _project_member_invitation(payload)
    if template == "shift_reminder":
        return _shift_reminder(payload)
    raise ValueError(f"Unsupported email template: {template}")


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
def _reservation_confirmation(payload: dict[str, str | None]) -> str:
    project_title = payload.get("project_title") or "Без названия"
    shift_title = payload.get("shift_title") or "Без названия"
    rows = [
        ("Проект", project_title),
        ("Смена", shift_title),
        ("Время", _time_range(payload.get("time_from"), payload.get("time_to"))),
    ]
    if payload.get("role"):
        rows.append(("Роль", payload["role"]))
    if payload.get("resource_type"):
        rows.append(("Ресурс", payload["resource_type"]))

    return _shell(
        preheader=f"Подтвердите участие в смене «{shift_title}».",
        eyebrow="Бронирование",
        heading="Подтвердите участие",
        lead=(
            "Вас назначили на смену в проекте "
            f"<strong style=\"color:{TEXT};\">{escape(project_title)}</strong>. "
            "Проверьте детали ниже и подтвердите участие."
        ),
        inner_html=_detail_card(rows),
        button_label="Подтвердить участие",
        button_url=payload.get("confirm_url") or "",
        footer_note="Вы получили это письмо, потому что вас добавили на смену в KinoFlow.",
    )


def _project_member_invitation(payload: dict[str, str | None]) -> str:
    project_title = payload.get("project_title") or "Без названия"
    role = payload.get("role") or "участник"
    rows = [("Проект", project_title), ("Роль", role)]

    return _shell(
        preheader=f"Вас пригласили в проект «{project_title}» в KinoFlow.",
        eyebrow="Приглашение",
        heading="Приглашение в проект",
        lead=(
            "Вас пригласили присоединиться к проекту "
            f"<strong style=\"color:{TEXT};\">{escape(project_title)}</strong>. "
            "Войдите в аккаунт и примите приглашение, чтобы начать работу."
        ),
        inner_html=_detail_card(rows),
        button_label="Принять приглашение",
        button_url=payload.get("accept_url") or "",
        footer_note="Если вы не ожидали это приглашение, просто проигнорируйте письмо.",
    )


def _shift_reminder(payload: dict[str, str | None]) -> str:
    project_title = payload.get("project_title") or "Без названия"
    shift_title = payload.get("shift_title") or "Без названия"
    rows = [
        ("Проект", project_title),
        ("Смена", shift_title),
        ("Время", _time_range(payload.get("time_from"), payload.get("time_to"))),
    ]
    if payload.get("role"):
        rows.append(("Роль", payload["role"]))

    inner = _detail_card(rows) + _resources_card(payload.get("resources"))

    return _shell(
        preheader=f"Смена «{shift_title}» скоро начнётся.",
        eyebrow="Напоминание о смене",
        heading="Смена скоро начнётся",
        lead=(
            "Напоминаем, что ваша смена в проекте "
            f"<strong style=\"color:{TEXT};\">{escape(project_title)}</strong> "
            "скоро начнётся. Вот всё, что нужно."
        ),
        inner_html=inner,
        button_label="Открыть смену",
        button_url=payload.get("shift_url") or "",
        footer_note="Вы получили это напоминание, потому что участвуете в этой смене.",
    )


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #
def _shell(
    *,
    preheader: str,
    eyebrow: str,
    heading: str,
    lead: str,
    inner_html: str,
    button_label: str,
    button_url: str,
    footer_note: str,
) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="ru" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="dark">
<title>{escape(heading)}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
body {{ margin:0; padding:0; background:{BG}; }}
a {{ text-decoration:none; }}
@media only screen and (max-width:620px) {{
  .kf-container {{ width:100% !important; }}
  .kf-pad {{ padding-left:22px !important; padding-right:22px !important; }}
}}
</style>
</head>
<body style="margin:0;padding:0;background:{BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;height:0;width:0;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{BG}"
  style="background:{BG};background-image:linear-gradient(180deg,{BG} 0%,{BG_SECONDARY} 100%);">
  <tr>
    <td align="center" style="padding:34px 16px 40px;font-family:{BODY_FONT};">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="kf-container" style="width:600px;max-width:600px;">
        <tr>
          <td class="kf-pad" style="padding:0 6px 22px;">{_brand_row()}</td>
        </tr>
        <tr>
          <td style="background:{SURFACE};background-image:linear-gradient(150deg,{SURFACE} 0%,{SURFACE_STRONG} 100%);border:1px solid {LINE};border-radius:18px;overflow:hidden;box-shadow:0 24px 50px rgba(0,0,0,0.45);">
            <div style="height:4px;background:{ACCENT};background-image:linear-gradient(135deg,{ACCENT} 0%,{ACCENT_STRONG} 100%);font-size:0;line-height:0;">&nbsp;</div>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td class="kf-pad" style="padding:34px 38px 38px;">
                  <p style="margin:0 0 14px;font-family:{HEAD_FONT};font-size:12px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{ACCENT};">{escape(eyebrow)}</p>
                  <h1 style="margin:0 0 14px;font-family:{HEAD_FONT};font-size:27px;line-height:1.18;font-weight:700;letter-spacing:-0.01em;color:{TEXT};">{escape(heading)}</h1>
                  <p style="margin:0 0 26px;font-size:15px;line-height:1.65;color:{TEXT_MUTED};">{lead}</p>
                  {inner_html}
                  {_button(button_label, button_url)}
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td class="kf-pad" style="padding:24px 14px 0;text-align:center;">
            <p style="margin:0 0 6px;font-size:12px;line-height:1.6;color:{TEXT_MUTED};">{escape(footer_note)}</p>
            <p style="margin:0;font-size:12px;color:rgba(168,180,200,0.7);">© {datetime.now().year} {_BRAND_NAME} · Управление проектами для съёмочных групп</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def _brand_row() -> str:
    return f"""\
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="vertical-align:middle;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="44" style="width:44px;height:44px;border-radius:13px;background:{ACCENT};background-image:linear-gradient(135deg,{ACCENT} 0%,{ACCENT_STRONG} 100%);text-align:center;vertical-align:middle;font-family:{HEAD_FONT};font-size:22px;font-weight:700;color:#ffffff;box-shadow:0 10px 24px rgba(255,138,42,0.30);">K</td>
          <td style="padding-left:13px;vertical-align:middle;font-family:{HEAD_FONT};font-size:19px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:{TEXT};">{_BRAND_NAME}</td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""


def _detail_card(rows: list[tuple[str, str]]) -> str:
    cells = []
    last = len(rows) - 1
    for index, (label, value) in enumerate(rows):
        border = "" if index == last else f"border-bottom:1px solid {LINE};"
        cells.append(
            f"""\
<tr>
  <td style="padding:11px 0;{border}font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:{TEXT_MUTED};white-space:nowrap;vertical-align:top;">{escape(label)}</td>
  <td style="padding:11px 0 11px 18px;{border}font-size:15px;font-weight:600;color:{TEXT};text-align:right;vertical-align:top;">{escape(value)}</td>
</tr>"""
        )
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SURFACE_STRONG};border:1px solid {LINE};border-radius:14px;margin:0 0 26px;">
  <tr><td style="padding:6px 20px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(cells)}</table>
  </td></tr>
</table>"""


def _resources_card(resources: str | None) -> str:
    items = [line.lstrip("-• ").strip() for line in (resources or "").splitlines()]
    items = [item for item in items if item]
    if not items:
        body = (
            f'<p style="margin:0;font-size:14px;color:{TEXT_MUTED};">'
            "Для этой смены ничего приносить не нужно.</p>"
        )
    else:
        rendered = "".join(
            f"""\
<tr>
  <td width="8" style="vertical-align:top;padding:7px 0 0;"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{ACCENT};"></span></td>
  <td style="padding:3px 0 3px 12px;font-size:14px;line-height:1.5;color:{TEXT};">{escape(item)}</td>
</tr>"""
            for item in items
        )
        body = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rendered}</table>'
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SURFACE_STRONG};border:1px solid {LINE};border-radius:14px;margin:0 0 26px;">
  <tr><td style="padding:18px 20px;">
    <p style="margin:0 0 12px;font-family:{HEAD_FONT};font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ACCENT};">Взять с собой</p>
    {body}
  </td></tr>
</table>"""


def _button(label: str, url: str) -> str:
    safe_url = escape(url, quote=True)
    safe_label = escape(label)
    return f"""\
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr><td>
    <!--[if mso]>
    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
      href="{safe_url}" style="height:48px;v-text-anchor:middle;width:240px;" arcsize="50%" fillcolor="{ACCENT}" stroke="f">
      <w:anchorlock/>
      <center style="color:#ffffff;font-family:{BODY_FONT};font-size:15px;font-weight:700;">{safe_label}</center>
    </v:roundrect>
    <![endif]-->
    <a href="{safe_url}"
      style="background:{ACCENT};background-image:linear-gradient(135deg,{ACCENT} 0%,{ACCENT_STRONG} 100%);border-radius:999px;color:#ffffff;display:inline-block;font-family:{BODY_FONT};font-size:15px;font-weight:700;line-height:48px;text-align:center;text-decoration:none;padding:0 34px;box-shadow:0 12px 28px rgba(255,138,42,0.30);mso-hide:all;">{safe_label}</a>
  </td></tr>
</table>"""


def _time_range(time_from: str | None, time_to: str | None) -> str:
    start = _pretty_dt(time_from)
    end = _pretty_dt(time_to)
    if start and end:
        return f"{start} → {end}"
    return start or end or "—"


_RU_MONTHS = (
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)


def _pretty_dt(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    return f"{parsed.day} {_RU_MONTHS[parsed.month - 1]} {parsed.year}, {parsed:%H:%M}"
