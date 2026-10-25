from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from . import __version__
from .backend import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    IMAGES_DIR,
    SHARE_DIR,
    LOG_DIR,
    USER_DATA,
    CardImage,
    detect_ports,
    ensure_prefix,
    inspect_image,
    known_images,
    launch_cardwriter,
    wine_binary,
)

CSS = b"""
.hero-title { font-size: 30px; font-weight: 800; letter-spacing: -0.6px; }
.hero-subtitle { font-size: 15px; }
.hero-icon { color: @accent_color; }
.warning { color: #e5a50a; }
.error { color: #e01b24; }
.success { color: #2ec27e; }
.mono { font-family: monospace; }
.step { padding: 2px 0; }
"""


def _display() -> Gdk.Display:
    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError("No graphical display is available.")
    return display


def _clipboard(text: str) -> None:
    _display().get_clipboard().set(text)


def _open_uri(uri: str) -> None:
    Gio.AppInfo.launch_default_for_uri(uri, None)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, initial_image: str | None = None, initial_port: str | None = None):
        super().__init__(
            application=application,
            title="Tech2 Card Writer",
            default_width=980,
            default_height=780,
        )
        self.set_size_request(720, 560)
        self.set_icon_name("tech2-cardwriter")
        self.initial_image = initial_image
        self.initial_port = initial_port
        self.images: list[CardImage] = []
        self.ports = []
        self.busy = False
        self._build_ui()
        initial_extra = []
        if initial_image:
            candidate = Path(initial_image).expanduser()
            if candidate.is_file():
                initial_extra.append(candidate)
        self.refresh_ports(select=initial_port)
        self.refresh_images(select=initial_image, extra=initial_extra)
        self._update_ready()
        GLib.idle_add(self._scroll_to_top)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        menu = Gio.Menu()
        menu.append("Documentation", "win.docs")
        menu.append("Open image folder", "win.image-folder")
        menu.append("About Tech2 Card Writer", "win.about")
        menu.append("Quit", "app.quit")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_button.set_tooltip_text("Main menu")
        header.pack_end(menu_button)
        toolbar.add_top_bar(header)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        clamp = Adw.Clamp(maximum_size=900, tightening_threshold=700)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                      margin_top=28, margin_bottom=36, margin_start=22, margin_end=22)
        clamp.set_child(box)
        scroll.set_child(clamp)
        toolbar.set_content(scroll)
        self.scroll = scroll

        # Persistent action bar so the primary action never scrolls away.
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_top=8, margin_bottom=10, margin_start=18, margin_end=18)
        self.progress = Gtk.ProgressBar()
        self.progress.set_visible(False)
        self.progress.set_pulse_step(0.08)
        self.status = Gtk.Label(label="", xalign=0)
        self.status.set_ellipsize(Pango.EllipsizeMode.END)
        self.status.add_css_class("dim-label")
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.END)
        self.launch_button = Gtk.Button(label="Launch Card Writer")
        self.launch_button.add_css_class("suggested-action")
        self.launch_button.add_css_class("pill")
        self.launch_button.set_size_request(-1, 46)
        self.launch_button.connect("clicked", lambda *_: self.on_launch())
        self.copy_button = Gtk.Button(label="Copy image path")
        self.copy_button.add_css_class("pill")
        self.copy_button.connect("clicked", lambda *_: self.on_copy_path())
        self.folder_button = Gtk.Button(label="Open image folder")
        self.folder_button.add_css_class("pill")
        self.folder_button.connect("clicked", lambda *_: self.on_open_folder())
        buttons.append(self.copy_button)
        buttons.append(self.folder_button)
        buttons.append(self.launch_button)
        bottom.append(self.progress)
        bottom.append(self.status)
        bottom.append(buttons)
        toolbar.add_bottom_bar(bottom)

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(toolbar)
        self.set_content(self.toast_overlay)

        # Hero
        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        icon = Gtk.Image.new_from_icon_name("tech2-cardwriter")
        icon.set_pixel_size(92)
        icon.add_css_class("hero-icon")
        hero.append(icon)
        hero_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        title = Gtk.Label(label="Tech 2 Card Writer", xalign=0)
        title.add_css_class("hero-title")
        subtitle = Gtk.Label(
            label="Write Saab and GM Tech 2 card images from Linux. "
                  "No Windows install, no TIS2000, no dongle.",
            xalign=0, wrap=True, max_width_chars=64,
        )
        subtitle.add_css_class("hero-subtitle")
        subtitle.add_css_class("dim-label")
        hero_text.append(title)
        hero_text.append(subtitle)
        hero.append(hero_text)
        box.append(hero)

        # Connection
        conn = Adw.PreferencesGroup(title="1 · Connect the Tech 2")
        conn.set_description("Use a USB-to-serial adapter (recommended) or a built-in serial port.")
        self.port_row = Adw.ActionRow(title="Serial port", subtitle="No serial ports detected")
        self.port_combo = Gtk.DropDown(model=Gtk.StringList.new(["No serial ports found"]))
        self.port_combo.set_sensitive(False)
        self.port_combo.set_tooltip_text("The port connected to the Tech 2 RS-232 cable")
        self.port_combo.connect("notify::selected", lambda *_: self._on_port_changed())
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER)
        refresh.set_tooltip_text("Scan for serial ports")
        refresh.connect("clicked", lambda *_: self.refresh_ports())
        suffix = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        suffix.append(self.port_combo)
        suffix.append(refresh)
        self.port_row.add_suffix(suffix)
        conn.add(self.port_row)
        box.append(conn)
        self.port_warning = Gtk.Label(label="", xalign=0, wrap=True)
        self.port_warning.add_css_class("warning")
        self.port_warning.set_visible(False)
        box.append(self.port_warning)

        # Image
        image_group = Adw.PreferencesGroup(title="2 · Choose a card image")
        image_group.set_description("The .bin file you want to write to the PCMCIA card.")
        self.image_row = Adw.ActionRow(title="Card image", subtitle="No .bin images found")
        self.image_combo = Gtk.DropDown(model=Gtk.StringList.new(["No images found"]))
        self.image_combo.set_sensitive(False)
        self.image_combo.set_size_request(360, -1)
        self.image_combo.connect("notify::selected", lambda *_: self._on_image_changed())
        choose = Gtk.Button(label="Choose…", valign=Gtk.Align.CENTER)
        choose.connect("clicked", lambda *_: self.choose_image())
        suffix2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        suffix2.append(self.image_combo)
        suffix2.append(choose)
        self.image_row.add_suffix(suffix2)
        image_group.add(self.image_row)
        box.append(image_group)

        self.image_details = Gtk.Label(label="", xalign=0, wrap=True)
        self.image_details.add_css_class("dim-label")
        box.append(self.image_details)
        self.image_warning = Gtk.Label(label="", xalign=0, wrap=True)
        self.image_warning.add_css_class("warning")
        self.image_warning.set_visible(False)
        box.append(self.image_warning)

        # Safety
        safety = Adw.PreferencesGroup(title="3 · Before you write")
        safety.set_description("A failed card write is recoverable, but it is inconvenient. Take your time.")
        self.chk_power = Gtk.CheckButton(label="The Tech 2 is powered from a 12 V adapter")
        self.chk_card = Gtk.CheckButton(label="The correct PCMCIA card is inserted")
        self.chk_risk = Gtk.CheckButton(label="I have a backup, or I accept the risk")
        for check in (self.chk_power, self.chk_card, self.chk_risk):
            check.connect("toggled", lambda *_: self._update_ready())
            row = Adw.ActionRow()
            row.add_prefix(check)
            row.set_activatable(True)
            row.connect("activated", lambda _row, c=check: c.set_active(not c.get_active()))
            safety.add(row)
        box.append(safety)

        # Steps
        expander = Gtk.Expander(label="What happens when I press Launch?")
        steps = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        margin_top=10, margin_bottom=6, margin_start=4, margin_end=4)
        for text in (
            "1. The app prepares a private Wine prefix on first launch (about 10–20 seconds).",
            "2. It exposes your serial port as COM1 inside Wine.",
            "3. Card Writer opens. Select COM1, click Start, then choose this same .bin file.",
            "4. Keep the Tech 2 on a stable 12 V supply. A 32 MB card takes about 15 minutes.",
            "5. When Card Writer reports success, close it and disconnect the Tech 2.",
        ):
            label = Gtk.Label(label=text, xalign=0, wrap=True)
            label.add_css_class("step")
            steps.append(label)
        expander.set_child(steps)
        box.append(expander)

        footer = Gtk.Label(xalign=0, wrap=True, use_markup=True)
        footer.set_markup(
            'This tool only writes the Tech 2 memory card. It does not program ECUs and is not TIS2000. '
            'Card Writer is © 2011 AlexRE. Card images are © Saab/GM; supply your own. '
            '<a href="https://tech2wiki.com/content/tech2_pcmcia/writing_pcmcia_cards/writing_pcmcia_using_tech2_card_writer.html">Read the Tech2Wiki guide</a>.'
        )
        footer.add_css_class("dim-label")
        footer.connect("activate-link", lambda _lbl, uri: (_open_uri(uri), True)[1])
        box.append(footer)

        # Actions
        app = self.get_application()
        for name, callback in (("docs", self.on_docs), ("about", self.on_about),
                               ("image-folder", self.on_open_folder), ("quit", lambda *_: app.quit())):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    # ------------------------------------------------------------- helpers
    def _scroll_to_top(self) -> bool:
        self.scroll.get_vadjustment().set_value(0)
        return False

    def toast(self, text: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(text))

    def selected_port(self):
        index = self.port_combo.get_selected()
        if index == Gtk.INVALID_LIST_POSITION or index < 0 or index >= len(self.ports):
            return None
        return self.ports[index]

    def selected_image(self) -> CardImage | None:
        index = self.image_combo.get_selected()
        if index == Gtk.INVALID_LIST_POSITION or index < 0 or index >= len(self.images):
            return None
        return self.images[index]

    def _select_port(self, device: str | None) -> None:
        if not device:
            return
        for i, port in enumerate(self.ports):
            if port.device == device:
                self.port_combo.set_selected(i)
                return

    def _select_image(self, path: str | None) -> None:
        if not path:
            return
        target = Path(path).expanduser().resolve()
        for i, image in enumerate(self.images):
            if image.path == target:
                self.image_combo.set_selected(i)
                return

    # -------------------------------------------------------------- ports
    def _on_port_changed(self) -> None:
        port = self.selected_port()
        if port is not None and not port.accessible:
            self.port_warning.set_label(
                f"Your user cannot open {port.device}. Add yourself to the dialout group: "
                "sudo usermod -aG dialout $USER   (then log out and back in)"
            )
            self.port_warning.set_visible(True)
        else:
            self.port_warning.set_visible(False)
        self._update_ready()

    def refresh_ports(self, select: str | None = None) -> None:
        extra = [os.environ["TECH2_PORT"]] if os.environ.get("TECH2_PORT") else []
        self.ports = detect_ports(extra)
        labels = []
        for port in self.ports:
            suffix = "" if port.accessible else "  (permission denied)"
            labels.append(port.label + suffix)
        if not labels:
            labels = ["No serial ports found"]
        self.port_combo.set_model(Gtk.StringList.new(labels))
        self.port_combo.set_sensitive(bool(self.ports))
        if self.ports:
            self.port_combo.set_selected(0)
            self._select_port(select)
            self.port_row.set_subtitle("Select the adapter connected to the Tech 2")
        else:
            self.port_row.set_subtitle("Plug in a USB-to-serial adapter, then press refresh")
        self._on_port_changed()

    # -------------------------------------------------------------- images
    def refresh_images(self, select: str | None = None, extra: list[Path] | None = None) -> None:
        self.images = known_images(extra or [])
        labels = [
            image.display_name + ("  ⚠" if not image.valid else ("  ⓘ" if image.warnings else ""))
            for image in self.images
        ]
        if not labels:
            labels = ["No .bin images found — choose one"]
        self.image_combo.set_model(Gtk.StringList.new(labels))
        self.image_combo.set_sensitive(bool(self.images))
        if self.images:
            self.image_combo.set_selected(0)
            self._select_image(select)
            self.image_row.set_subtitle("Pick the image that matches your car and card size")
        else:
            self.image_row.set_subtitle("Use Choose… to pick a .bin file from anywhere")
        self._on_image_changed()

    def _on_image_changed(self) -> None:
        image = self.selected_image()
        if image is None:
            self.image_details.set_label("")
            self.image_warning.set_visible(False)
            self._update_ready()
            return
        details = f"{image.version_label}  ·  {image.coverage or 'No known coverage metadata'}  ·  {image.size_mb:g} MB"
        self.image_details.set_label(details)
        if image.warnings:
            self.image_warning.set_label("  ".join(image.warnings))
            self.image_warning.remove_css_class("warning")
            self.image_warning.remove_css_class("dim-label")
            self.image_warning.add_css_class("warning" if not image.valid else "dim-label")
            self.image_warning.set_visible(True)
        else:
            self.image_warning.set_visible(False)
        self._update_ready()

    def choose_image(self) -> None:
        dialog = Gtk.FileDialog(title="Choose a Tech 2 card image")
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Tech 2 card images (*.bin)")
        file_filter.add_pattern("*.bin")
        file_filter.add_pattern("*.BIN")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(file_filter)
        dialog.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        if gfile is None or gfile.get_path() is None:
            return
        path = Path(gfile.get_path())
        self.refresh_images(select=str(path), extra=[path])

    # -------------------------------------------------------------- state
    def _all_checks(self) -> bool:
        return self.chk_power.get_active() and self.chk_card.get_active() and self.chk_risk.get_active()

    def _update_ready(self) -> None:
        image = self.selected_image()
        port = self.selected_port()
        ready = bool(
            not self.busy
            and port is not None
            and port.accessible
            and image is not None
            and image.valid
            and self._all_checks()
        )
        self.launch_button.set_sensitive(ready)
        if self.busy:
            return
        if port is None:
            self.status.set_label("Connect the Tech 2 serial cable to continue.")
        elif not port.accessible:
            self.status.set_label(f"Permission denied for {port.device}. Add your user to the dialout group, then log out and back in.")
        elif image is None:
            self.status.set_label("Choose a card image to continue.")
        elif not image.valid:
            self.status.set_label("This file does not look like a valid Tech 2 card image.")
        elif not self._all_checks():
            self.status.set_label("Confirm the three checks above to enable writing.")
        else:
            self.status.set_label("Ready. Launch Card Writer, select COM1, then Start.")

    # ------------------------------------------------------------- launch
    def on_launch(self) -> None:
        image = self.selected_image()
        port = self.selected_port()
        if image is None or port is None or self.busy:
            return
        if not self._all_checks():
            self.toast("Please confirm the three checks first.")
            return
        self.busy = True
        self.launch_button.set_sensitive(False)
        self.progress.set_visible(True)
        self.progress.pulse()
        self.status.set_label("Preparing the Wine environment — first run only…")
        GLib.timeout_add(120, self._pulse)

        def worker():
            try:
                created = ensure_prefix()
                proc, log = launch_cardwriter(port.device)
                GLib.idle_add(self._launch_done, image, proc, log, created, None)
            except Exception as exc:  # noqa: BLE001 - show the user the real error
                GLib.idle_add(self._launch_done, image, None, None, False, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _pulse(self) -> bool:
        if self.progress.get_visible():
            self.progress.pulse()
            return True
        return False

    def _launch_done(self, image: CardImage, proc, log, created: bool, error: str | None) -> bool:
        self.busy = False
        self.progress.set_visible(False)
        self._update_ready()
        if error:
            self._alert("Card Writer could not start", error)
            return False
        self.status.set_label(f"Card Writer is running. Log: {log}" if log else "Card Writer is running.")
        body = (
            "Card Writer is open in its own window.\n\n"
            f"1. Select COM1 (your {self.selected_port().device if self.selected_port() else 'serial port'}).\n"
            f"2. Click Start and choose:\n{image.path}\n\n"
            "3. Keep the Tech 2 on 12 V and do not disconnect it until the write finishes."
        )
        dialog = Adw.AlertDialog(heading="Card Writer is ready", body=body)
        dialog.add_response("close", "Close")
        dialog.add_response("copy", "Copy image path")
        dialog.set_default_response("copy")
        dialog.set_close_response("close")
        dialog.connect("response", self._on_launch_response, image)
        dialog.present(self)
        return False

    def _on_launch_response(self, dialog: Adw.AlertDialog, response: str, image: CardImage) -> None:
        if response == "copy":
            _clipboard(str(image.path))
            self.toast("Image path copied.")

    def _alert(self, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("close", "Close")
        dialog.set_close_response("close")
        dialog.present(self)

    # ------------------------------------------------------------- actions
    def on_copy_path(self) -> None:
        image = self.selected_image()
        if image is None:
            self.toast("Choose an image first.")
            return
        _clipboard(str(image.path))
        self.toast("Image path copied.")

    def on_open_folder(self, *_args) -> None:
        image = self.selected_image()
        folder = image.path.parent if image else IMAGES_DIR
        folder.mkdir(parents=True, exist_ok=True)
        _open_uri(folder.as_uri())

    def on_docs(self, *_args) -> None:
        _open_uri("https://tech2wiki.com/content/tech2_pcmcia/writing_pcmcia_cards/writing_pcmcia_using_tech2_card_writer.html")

    def on_about(self, *_args) -> None:
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon="tech2-cardwriter",
            developer_name="Tech2 Card Writer contributors",
            version=APP_VERSION,
            comments="A modern Linux front-end for writing Saab and GM Tech 2 PCMCIA card images.",
            website="https://github.com/ogden-marrow/tech2-cardwriter-linux",
            issue_url="https://github.com/ogden-marrow/tech2-cardwriter-linux/issues",
            license_type=Gtk.License.MIT_X11,
            developers=["Tech2 Card Writer contributors"],
        )
        about.present(self)


class Application(Adw.Application):
    def __init__(self, initial_image: str | None = None, initial_port: str | None = None, **kwargs):
        super().__init__(application_id=APP_ID, **kwargs)
        self.initial_image = initial_image
        self.initial_port = initial_port
        self.window = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        icon_theme = Gtk.IconTheme.get_for_display(_display())
        icon_path = SHARE_DIR / "icons"
        if icon_path.is_dir():
            icon_theme.add_search_path(str(icon_path))
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            _display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.set_accels_for_action("app.quit", ["<primary>q"])
        self.set_accels_for_action("win.docs", ["F1"])

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(self, self.initial_image, self.initial_port)
        self.window.present()
