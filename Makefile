VERSION = $(shell git describe --tags)
GTK = gtk+-3.0
VTE = vte-2.91
PREFIX ?= /usr/local
BINDIR ?= ${PREFIX}/bin
DATADIR ?= ${PREFIX}/share
MANDIR ?= ${DATADIR}/man

CXXFLAGS := -std=c++11 -O3 \
	    -Wall -Wextra -pedantic \
	    -Winit-self \
	    -Wshadow \
	    -Wformat=2 \
	    -Wmissing-declarations \
	    -Wstrict-overflow=5 \
	    -Wcast-align \
	    -Wconversion \
	    -Wunused-macros \
	    -Wwrite-strings \
	    -DNDEBUG \
	    -D_POSIX_C_SOURCE=200809L \
	    -DMANTID_VERSION=\"${VERSION}\" \
	    ${shell pkg-config --cflags ${GTK} ${VTE}} \
	    ${CXXFLAGS}

ifeq (${CXX}, g++)
	CXXFLAGS += -Wno-missing-field-initializers
endif

ifeq (${CXX}, clang++)
	CXXFLAGS += -Wimplicit-fallthrough
endif

LDFLAGS := -s -Wl,--as-needed ${LDFLAGS}
LDLIBS := ${shell pkg-config --libs ${GTK} ${VTE}}

mantid: mantid.cc url_regex.hh util/clamp.hh util/maybe.hh util/memory.hh keybindings.hh keybindings_insert.hh keybindings_cmd.hh
	${CXX} ${CXXFLAGS} ${LDFLAGS} $< ${LDLIBS} -o $@

install: mantid mantid.desktop
	install -Dm755 mantid ${DESTDIR}${BINDIR}/mantid
	install -Dm644 config ${DESTDIR}/etc/xdg/mantid/config
	install -Dm644 mantid.desktop ${DESTDIR}${DATADIR}/applications/mantid.desktop
	install -Dm644 man/mantid.1 ${DESTDIR}${MANDIR}/man1/mantid.1
	install -Dm644 man/mantid.config.5 ${DESTDIR}${MANDIR}/man5/mantid.config.5

clean:
	rm mantid

.PHONY: clean install
