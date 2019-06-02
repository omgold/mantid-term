#define KEYDEF0(label) label,
#define KEYDEF0_DUP(label)
#define KEYDEF(label, binding) label,
#define KEYDEF_DUP(label, binding)
#define KEYDEF2(label, binding1, binding2) label,
#define KEYDEF3(label, binding1, binding2, binding3) label,
#define KEYDEF_CHARS(binding, chars)

enum class command_id {
    #include "keybindings_insert.hh"
    #include "keybindings_cmd.hh"
    inject_chars,
    none,
};

#undef KEYDEF0
#undef KEYDEF0_DUP
#undef KEYDEF
#undef KEYDEF_DUP
#undef KEYDEF2
#undef KEYDEF3
#undef KEYDEF_CHARS

#define KEYDEF0(label)
#define KEYDEF0_DUP(label)
#define KEYDEF(label, binding) { binding, { command_id:: label, NULL } },
#define KEYDEF_DUP(label, binding) KEYDEF(label, binding)
#define KEYDEF2(label, binding1, binding2) KEYDEF(label, binding1) KEYDEF(label, binding2)
#define KEYDEF3(label, binding1, binding2, binding3) KEYDEF2(label, binding1, binding2) KEYDEF(label, binding3)
#define KEYDEF_CHARS(binding, chars) { binding, { command_id::inject_chars, chars } },

static std::map<accelerator,keybinding> default_keybindings_insert = {
    #include "keybindings_insert.hh"
};

static std::map<accelerator,keybinding> default_keybindings_cmd = {
    #include "keybindings_cmd.hh"
};

typedef std::vector<std::pair<const char*,command_id> > command_name_set;

#undef KEYDEF0
#undef KEYDEF0_DUP
#undef KEYDEF
#undef KEYDEF_DUP
#undef KEYDEF2
#undef KEYDEF3
#undef KEYDEF_CHARS
#define KEYDEF0(label) std::make_pair(#label, command_id:: label),
#define KEYDEF0_DUP(label) KEYDEF0(label)
#define KEYDEF(label, binding1) KEYDEF0(label)
#define KEYDEF_DUP(label, binding1) KEYDEF0(label)
#define KEYDEF2(label, binding1, binding2) KEYDEF0(label)
#define KEYDEF3(label, binding1, binding2, binding3) KEYDEF0(label)
#define KEYDEF_CHARS(binding, chars)

static command_name_set command_names_insert = {
    #include "keybindings_insert.hh"
};

static command_name_set command_names_cmd = {
    #include "keybindings_cmd.hh"
};
