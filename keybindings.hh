#define KEYDEF_DUP(label, binding)
#define KEYDEF2(label, binding1, binding2) KEYDEF(label, 0)
#define KEYDEF3(label, binding1, binding2, binding3) KEYDEF(label, 0)
#define KEYDEF_CHARS(binding, chars)

enum class command_id {
#define KEYDEF(label, binding) label,
    #include "keybindings_insert.hh"
#undef KEYDEF
#define KEYDEF(label, binding) label,
    #include "keybindings_cmd.hh"
    inject_chars,
    none,
};

#undef KEYDEF_DUP
#undef KEYDEF2
#undef KEYDEF3
#undef KEYDEF_CHARS

#define KEYDEF_DUP(label, binding) KEYDEF(label, binding)
#define KEYDEF2(label, binding1, binding2) KEYDEF(label, binding1) KEYDEF(label, binding2)
#define KEYDEF3(label, binding1, binding2, binding3) KEYDEF2(label, binding1, binding2) KEYDEF(label, binding3)
#define KEYDEF_CHARS(binding, chars) { binding, { command_id::inject_chars, chars } },

static std::map<accelerator,keybinding> default_keybindings_insert = {
#undef KEYDEF
#define KEYDEF(label, binding) { binding, { command_id:: label, NULL } },
    #include "keybindings_insert.hh"
};

static std::map<accelerator,keybinding> default_keybindings_cmd = {
#undef KEYDEF
#define KEYDEF(label, binding) { binding, { command_id:: label, NULL } },
    #include "keybindings_cmd.hh"
};

typedef std::vector<std::pair<const char*,command_id> > command_name_set;

#undef KEYDEF2
#undef KEYDEF3
#undef KEYDEF_CHARS
#define KEYDEF2(label, binding1, binding2) KEYDEF(label, 0)
#define KEYDEF3(label, binding1, binding2, binding3) KEYDEF(label, 0)
#define KEYDEF_CHARS(binding, chars)

static command_name_set command_names_insert = {
#undef KEYDEF
#define KEYDEF(label, binding) std::make_pair(#label, command_id:: label),
    #include "keybindings_insert.hh"
};

static command_name_set command_names_cmd = {
#undef KEYDEF
#define KEYDEF(label, binding) std::make_pair(#label, command_id:: label),
    #include "keybindings_cmd.hh"
};
