import sys
import os
import yaml
import argparse

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Vte
from gi.repository import Pango

from .colors import rgba_parse, default_palette, default_colors, transparent
from .keybindings import default_keybindings


def introspect(obj):
    cleaned_obj = { entry for entry in dir(obj) if not entry.startswith("__") }
    print(cleaned_obj)


def get_key_name(keyval, modifiers):
    label = Gtk.accelerator_name(keyval, modifiers)
    check_keyval, check_modifiers = Gtk.accelerator_parse(label)
    if check_keyval == keyval and check_modifiers == modifiers:
        return label


def child_exited_cb(vte, status, terminal):
    app.terminals.remove(terminal)
    if len(app.terminals) == 0:
        Gtk.main_quit()
        sys.exit(status//256)


def exit_with_success(window):
    Gtk.main_quit()
    sys.exit(0)


def key_press_cb(vte, key, terminal):

    command_mode = terminal.command_mode
    if command_mode:
        action = app.find_keybinding(app.keybindings_command, key,
                                     debug_print=app.print_accelerators)
    else:
        action = app.find_keybinding(app.keybindings_normal, key)

    if action is not None:
        try:
            action_name, cmd, args = action
            ret = cmd(terminal, **args)
            return ret is not False
        except Exception as e:
            if isinstance(args,dict):
                args = [ "%s=%s" % (key,arg) for key, arg in args.items() ]
            else:
                args = [ str(arg) for arg in args ]
            print("exception during invocation of action %s(%s):\n%s" % (action_name, ", ".join(args), e), file=sys.stderr)
            return True

    if command_mode:
        return True
    return False


def entry_key_press_cb():
    pass


def get_entry_position_overlay_cb(overlay, entry, allocation):

    hbox = overlay.get_child()

    width  = hbox.get_allocated_width()
    height = hbox.get_allocated_height()

    min_size, natural_size = entry.get_preferred_size()

    allocation.x = width - natural_size.width - 40
    allocation.y = 0
    allocation.width  = min(width, natural_size.width)
    allocation.height = min(height, natural_size.height)


# def button_press_cb():
#    pass

# def focus_cb():
#    pass

def alpha_screen_changed_cb(window):
    pass


def window_state_cb(vte, event):
    app.is_fullscreen = event.new_window_state & Gdk.WindowState.FULLSCREEN
    return False


def window_title_cb(vte, terminal):
    if app.dynamic_title and terminal == app.active_terminal:
        vte.get_toplevel().set_title(vte.get_window_title())
    pass


# def spawn_child_cb(pty, task, terminal):
#     if task.had_error():
#         try:
#             task.propagate_int()
#         except GLib.Error as e:
#             print(e.message)
#         child_exited_cb(terminal.vte, 127, terminal)
#         return

#     result = pty.spawn_finish(task)
#     pid = result[0]
#     terminal.vte.watch_child(pid)


class Terminal:
    def __init__(self, keep_open):

        self.command_mode = False
        self.select_mode = None
        self.selection_start = None
        self.normal_cursor_position = None

        self.vte = Vte.Terminal()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        Gtk.StyleContext.add_class(hbox.get_style_context(),"mantid")

        self.hint_overlay = Gtk.Overlay()
        self.hint_overlay.override_background_color(Gtk.StateFlags.NORMAL,transparent)

        self.scrollbar = Gtk.Scrollbar.new(Gtk.Orientation.VERTICAL, self.vte.get_vadjustment())

        self.da = Gtk.DrawingArea()
        self.da.override_background_color(Gtk.StateFlags.NORMAL,transparent)
        self.da.set_halign(Gtk.Align.FILL)
        self.da.set_valign(Gtk.Align.FILL)

        self.panel_overlay = Gtk.Overlay()

        self.panel_entry = Gtk.Entry()
        self.panel_entry.set_margin_start(5)
        self.panel_entry.set_margin_end(5)
        self.panel_entry.set_margin_top(5)
        self.panel_entry.set_margin_bottom(5)
        self.panel_entry.set_halign(Gtk.Align.START)
        self.panel_entry.set_valign(Gtk.Align.END)
        self.panel_entry.connect("key-press-event", entry_key_press_cb, self)
        self.panel_overlay.connect("get-child-position", get_entry_position_overlay_cb)

        self.vte.connect("child-exited", child_exited_cb, self)
        self.vte.connect("key-press-event", key_press_cb, self)
        #self.vte.connect("button-press-event", button_press_cb, self)
        self.vte.connect("window-title-changed", window_title_cb, self)

        self.hint_overlay.add_overlay(self.da)
        self.hint_overlay.add(self.vte)
        hbox.pack_start(self.hint_overlay, True, True, 0)
        hbox.pack_start(self.scrollbar, False, False, 0)
        self.panel_overlay.add(hbox)
        # self.panel_overlay.add_overlay(self.panel_entry)

        self.panel_overlay.show_all()

        self.apply_config()

        self.panel_entry.hide()
        self.da.hide()
        self.vte.grab_focus()


    def apply_config(self):

        vte = self.vte

        startup = app.config["startup"]
        appearance = app.config["appearance"]

        if appearance["show-scrollbar"]:
            self.scrollbar.show()
        else:
            self.scrollbar.hide()

        vte.set_scrollback_lines(startup["scrollback-lines"])

        font = Pango.font_description_from_string(appearance["font"])
        vte.set_font(font)

        vte.set_colors(None, None, app.palette)
        vte.set_color_background(app.colors["background"])
        foreground = app.colors["foreground"]
        vte.set_color_foreground(foreground)
        vte.set_color_bold(app.colors.get("foreground-bold",foreground))
        vte.set_color_cursor(app.colors.get("cursor"))
        vte.set_color_cursor_foreground(app.colors.get("cursor-foreground"))
        vte.set_color_highlight(app.colors.get("highlight"))
        vte.set_color_highlight_foreground(app.colors.get("highlight-foreground"))


    def run(self, cmd):
        env = os.environ.copy()

        gdk_window = app.window.get_window()
        if isinstance(gdk_window,gi.repository.GdkX11.X11Window):
            env["WINDOWID"] = gdk_window.get_xid()

        startup = app.config["startup"]

        env["TERM"] = startup["term"]

        #draw_cb_info draw_cb_info{vte, &info.panel, &info.config.hints, info.config.filter_unmatched_urls};
        #g_signal_connect_swapped(info.panel.da, "draw", G_CALLBACK(draw_cb), &draw_cb_info);

        # pty = self.vte.pty_new_sync(Vte.PtyFlags.DEFAULT, None)

        # pty.spawn_async(None, # pwd
        #                 cmd, # cmd
        #                 None, # env
        #                 GLib.SpawnFlags.SEARCH_PATH|GLib.SpawnFlags.DO_NOT_REAP_CHILD, # spawn_flags
        #                 None, # child_setup_data,
        #                 None, # child_setup_data_destroy,
        #                 -1, # timeout,
        #                 None, # cancellable
        #                 spawn_child_cb, # callback
        #                 self, # user_data
        # )

        # self.vte.set_pty(pty)

        self.vte.spawn_sync(Vte.PtyFlags.DEFAULT,
                            None, # pwd
                            cmd, # cmd
                            [ "%s=%s" % entry for entry in env.items()], # env
                            GLib.SpawnFlags.SEARCH_PATH, # spawn_flags
                            None, # child_setup_data,
                            None, # child_setup_data_destroy,
                            None, # cancellable
        )


    def update_scroll(self):

        vte = self.vte

        adjustment = vte.get_vadjustment()
        scroll_row = adjustment.get_value()
        row_count = vte.get_row_count()
        _, cursor_row = vte.get_cursor_position()

        #print(cursor_row, row_count, scroll_row)
        if cursor_row < scroll_row:
            adjustment.set_value(cursor_row)
        elif cursor_row - row_count >= scroll_row:
            adjustment.set_value(cursor_row-row_count+1)


    def update_selection(self):

        vte = self.vte

        col_count = vte.get_column_count()
        cursor_col, cursor_row = vte.get_cursor_position()

        mode = self.select_mode
        if mode is None:
            return

        start_col, start_row = self.selection_start

        vte.set_selection_block_mode(self.select_mode == "block")

        if mode == "standard":
            start = start_row * col_count + start_col;
            end = cursor_row * col_count + cursor_col;
            if start < end:
                vte.select_text(start_col, start_row,
                                cursor_col, cursor_row)
            else:
                vte.select_text(cursor_col, cursor_row,
                                start_col, start_row)
        elif mode == "line":
            vte.select_text(0, min(start_row, cursor_row),
                            col_count-1, max(start_row, cursor_row))
        elif mode == "block":
            vte.select_text(min(start_col, cursor_col), min(start_row, cursor_row),
                            max(start_col, cursor_col), max(start_row, cursor_row))


    def start_select(self, mode):
        self.selection_start = self.vte.get_cursor_position()
        self.select_mode = mode
        self.update_selection()


    def stop_select(self):
        self.selection_start = None
        self.select_mode = None
        self.vte.unselect_all()


    def yank_selection(self, dest):
        if dest == "primary":
            self.select_mode = None
            self.stop_select()
        elif dest == "clipboard":
            self.select_mode = None
            self.stop_select()

    def paste_selection(self, dest):
        if dest == "primary":
            self.vte.paste_primary()
        elif dest == "clipboard":
            self.vte.paste_clipboard()


def action_inject_keys(terminal, chars):
    if isinstance(chars, str):
        chars = chars.encode("utf-8")
    terminal.vte.feed_child_binary(chars)


def action_move(terminal, x=0, y=0, screen=0, row=None):

    vte = terminal.vte

    end_col = vte.get_column_count()-1
    cursor_col, cursor_row = vte.get_cursor_position()
    adjustment = vte.get_vadjustment()
    mode = vte.get_cursor_blink_mode()
    vte.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)
    if row is not None:
        base_x = vte.get_column_count() * row
    else:
        base_x = cursor_col
    dest_x = min(max(base_x+x, 0), end_col)
    dest_y = cursor_row+y
    if screen != 0:
        dest_y += vte.get_row_count() * screen
    dest_y = min(max(dest_y,adjustment.get_lower()),adjustment.get_upper()-1)
    vte.set_cursor_position(dest_x, dest_y)

    terminal.update_scroll()
    terminal.update_selection()
    vte.set_cursor_blink_mode(mode)


def action_scroll(terminal, y=0, screen=0):
    vte = terminal.vte

    adjustment = vte.get_vadjustment()
    dest = adjustment.get_value()
    if screen != 0:
        dest += vte.get_row_count() * screen
    dest += y
    adjustment.set_value(dest);

def action_enter_command_mode(terminal):
    terminal.normal_cursor_position = terminal.vte.get_cursor_position()
    terminal.command_mode = True


def action_leave_command_mode(terminal):
    terminal.vte.set_cursor_position(*terminal.normal_cursor_position)
    terminal.command_mode = False
    if terminal.select_mode is not None:
        terminal.stop_select()


def action_enter_select_mode(terminal, mode="standard"):
    if mode not in ("standard", "line", "block"):
        return
    terminal.start_select(mode)


def action_leave_select_mode(terminal):
    if terminal.select_mode is not None:
        terminal.stop_select()


def action_yank_selection(terminal, dest="clipboard", leave_command_mode=False):
    terminal.yank_selection(dest)
    if leave_command_mode:
        action_leave_command_mode(terminal)


def action_paste_selection(terminal, src="clipboard"):
    terminal.paste_selection(src)


def action_zoom(terminal, set=None, change=0):
    scale = app.font_scale
    #introspect(Pango.SCALE)
    if set is not None:
        scale = set
    scale *= (1+change)
    if scale < 0.1 or scale > 10:
        return
    app.set_font_scale(scale)


def action_fullscreen(terminal, set=None, toggle=False):
    if set is not None:
        if set:
            app.is_fullscreen = True
        else:
            app.is_fullscreen = False
    if toggle:
        app.is_fullscreen = not app.is_fullscreen
    if app.is_fullscreen:
        app.window.fullscreen()
    else:
        app.window.unfullscreen()


def action_reload_config(terminal):
    app.load_config()
    app.apply_config()


actions = {
    "global": {
        "yank-selection": action_yank_selection,
        "zoom": action_zoom,
        "scroll": action_scroll,
        "fullscreen": action_fullscreen,
        "reload-config": action_reload_config,
    },
    "normal": {
        "enter-command-mode": action_enter_command_mode,
        "inject-keys": action_inject_keys,
        "paste-selection": action_paste_selection,
    },
    "command": {
        "leave-command-mode": action_leave_command_mode,
        "move": action_move,
        "start-select": action_enter_select_mode,
        "end-select": action_leave_select_mode,
    },
}


class App:

    def __init__(self):

        parser = argparse.ArgumentParser(prog="mantid",
                                         description="keyboard-controllable terminal")
        parser.add_argument('COMMAND', help='command to execute', nargs='*')
        parser.add_argument('-v', '--version', help='version info', action="store_true")
        parser.add_argument('-d', '--pwd', help='working directory', default='.')
        parser.add_argument('-r', '--role', help='window role')
        parser.add_argument('-t', '--title', help='window title')
        parser.add_argument('-k', '--keep-open', help='keep window open after child exits')
        parser.add_argument('-f', '--fullscreen', help='start in fullscreen mode', action="store_true")
        parser.add_argument('-c', '--config', help='config file', default=os.environ.get("HOME","")+"/.config/mantid.yaml")
        parser.add_argument('-i', '--icon', help='window icon')
        parser.add_argument('-a', '--print-accelerators', help='print key accelerator names in command mode', action="store_true")

        self.args = parser.parse_args()
        self.load_config()

        self.terminals = []
        self.active_terminal = None
        self.is_fullscreen = False


    def setup(self):
        self.hint_overlay = Gtk.Overlay()

        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.connect("destroy", exit_with_success)

        # self.window.connect("focus-in-event", focus_cb)
        # self.window.connect("focus-out-event", focus_cb)
        self.window.connect("screen-changed", alpha_screen_changed_cb)
        self.window.connect("window-state-event", window_state_cb)

        alpha_screen_changed_cb(self.window)

        self.print_accelerators = self.args.print_accelerators

        startup = self.config["startup"]

        keep_open = self.args.keep_open or startup["keep-open"]

        fullscreen = self.args.fullscreen or startup["fullscreen"]
        if fullscreen:
            action_fullscreen(None, set=fullscreen)

        self.apply_config()

        if len(self.args.COMMAND) != 0:
            cmd = self.args.COMMAND
        else:
            cmd = startup["shell"]
            if isinstance(cmd, str):
                cmd = [ cmd ]

        self.add_terminal(keep_open)
        self.set_active_terminal(self.terminals[0])

        self.active_terminal.vte.set_size(startup["columns"], startup["rows"])
        self.set_font_scale( self.config["startup"]["font-scale"] )

        self.window.show()

        self.active_terminal.run(cmd)


    def load_config(self):

        self.config = {
            "startup": {
                "term": "xterm-256color",
                "role": None,
                "keep-open": False,
                "fullscreen": False,
                "shell": os.environ.get("SHELL","/bin/sh"),
                "rows": 25,
                "columns": 80,
                "font-scale": 1.,
                "scrollback-lines": 1000,
            },
            "appearance": {
                "show-scrollbar": True,
                "icon": "terminal",
                "font": "Monospace",
                "colors": {},
            },
            "keybindings": {
            },
        }

        if os.path.exists(self.args.config):
            try:
                config_file = yaml.safe_load( open( self.args.config, "r" ) )
            except yaml.YAMLError as e:
                print("yaml:",e, file=sys.stderr)
                config_file = {}
            except IOError as e:
                print("config:",e, file=sys.stderr)
                config_file = {}
        else:
            config_file = {}

        for section_name, section in self.config.items():
            file_section = config_file.get(section_name, {})
            if isinstance(file_section, dict):
                self.config[section_name].update(file_section)
            else:
                print("config: section", section_name, "needs to be a mapping. Will be ignored.", file=sys.stderr)

        self.colors = default_colors.copy()
        self.colors.update( { key: rgba_parse(value)
                              for key, value in self.config["appearance"]["colors"].items() } )

        self.palette = default_palette.copy()

        for i in range(256):
            color = self.colors.get(i)
            if color is not None:
                self.palette[i] = color

        self.keybindings = {}
        for s in ("global","normal","command"):
            b = default_keybindings[s].copy()
            b.update(self.config["keybindings"].get(s,{}))
            a = {}

            for key, action in b.items():
                acc = Gtk.accelerator_parse(key)
                #print(acc)
                if acc.accelerator_key == 0:
                    print("keybindings:", "accelerator ", key, "failed to parse. Will be ignored.", file=sys.stderr)
                    continue
                binding = acc.accelerator_key, acc.accelerator_mods
                if action is None:
                    continue
                if isinstance(action, str):
                    action_name = action
                    args = {}
                else:
                    action_name = action.get("action","undefined")
                    args = action
                    try:
                        del args["action"]
                    except KeyError:
                        pass
                cmd = actions[s].get(action_name) or actions["global"].get(action_name)
                if cmd is None:
                    args = [ "%s=%s" % (key,arg) for key, arg in args.items() ]
                    print("keybindings: action %s(%s) bound to %s is not defined. Will be ignored." %
                          (action_name, ", ".join(args), key), file=sys.stderr)
                    continue
                action = action_name, cmd, args

                a[binding] = action

            self.keybindings[s] = a

        self.keybindings_normal = self.keybindings["global"].copy()
        self.keybindings_normal.update(self.keybindings["normal"])
        self.keybindings_command = self.keybindings["global"].copy()
        self.keybindings_command.update(self.keybindings["command"])


    def apply_config(self):

        startup = self.config["startup"]
        appearance = self.config["appearance"]

        if self.args.role is not None:
            role = self.args.role
        else:
            role = startup["role"]

        if role is not None:
            window.set_role(self.args.role)

        if self.args.title is not None:
            self.window.set_title(self.args.title)
            self.dynamic_title = False
        else:
            if self.active_terminal is not None:
                window_title_cb(self.active_terminal.vte, self.active_terminal)
            self.dynamic_title = True

        if self.args.icon is not None:
            icon = self.args.icon
        else:
            icon = appearance["icon"]

        self.window.set_icon_name(icon)

        for terminal in self.terminals:
            terminal.apply_config()


    def set_font_scale(self, scale):
        for term in self.terminals:
            term.vte.set_font_scale(scale)
        self.font_scale = scale


    def add_terminal(self, keep_open):
        terminal = Terminal(keep_open)
        self.terminals.append(terminal)


    def set_active_terminal(self, terminal):
        self.active_terminal = terminal
        self.window.add(terminal.panel_overlay)


    def find_keybinding(self, binding_map, event, debug_print=False):
        display = app.window.get_window().get_display()
        keymap = Gdk.Keymap.get_for_display(display)
        intent_default_mod_mask = keymap.get_modifier_mask(Gdk.ModifierIntent.DEFAULT_MOD_MASK)

        #print("r",event.hardware_keycode, event.state)
        #introspect(Gdk.ModifierType)

        # 'direct' match
        modifiers = event.state

        t = keymap.translate_keyboard_state(event.hardware_keycode, modifiers, event.group)
        consumed_modifiers = t.consumed_modifiers
        result_keyval = t.keyval
        result_modifiers = modifiers & intent_default_mod_mask
        result_modifiers &= Gdk.ModifierType(~consumed_modifiers)

        if debug_print:
            label1 = get_key_name(result_keyval, result_modifiers)

        action = binding_map.get((result_keyval, result_modifiers))
        if action is not None:
            if debug_print:
                if label1 is not None:
                    print( "key '%s' pressed" % label1, file=sys.stderr)
            return action
        #print("n",result_keyval, result_modifiers)

        # match keyval converted without modifiers
        if (modifiers & intent_default_mod_mask):
            #print("c",modifiers & Gdk.ModifierType(~intent_default_mod_mask))
            t = keymap.translate_keyboard_state(event.hardware_keycode,
                                                modifiers & Gdk.ModifierType(~intent_default_mod_mask), event.group)
            result_keyval = t.keyval
            result_modifiers = modifiers & intent_default_mod_mask
            #result_modifiers = modifiers
            #result_modifiers &= intent_default_mod_mask | Gdk.ModifierType(~consumed_modifiers)
            #print("e",result_keyval, result_modifiers)

            if debug_print:
                label2 = get_key_name(result_keyval, result_modifiers)
                if label1 == label2:
                    label2 = None
                if label1 is None:
                    label1 = label2
                    label2 = None
                if label1 is not None:
                    if label2 is None:
                        print( "key '%s' pressed" % label1, file=sys.stderr)
                    else:
                        print( "key '%s' aka '%s' pressed" % (label1,label2), file=sys.stderr)
            action = binding_map.get((result_keyval, result_modifiers))
            if action is not None:
                return action

        else:
            if debug_print:
                print( "key '%s' pressed" % label1, file=sys.stderr)

#introspect(Gio.Cancellable)

def main():
#if __name__ == "__main__":
    global app
    app = App()
    app.setup()
    Gtk.main()
