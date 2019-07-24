all: libmantid.so Mantid-1.0.typelib

libmantid.so: libmantid.c
	gcc -O2 -I vte-ng/src/ `pkg-config --cflags gtk+-3.0` -shared -fpic $< -o $@

Mantid-1.0.typelib: Mantid-1.0.gir
	g-ir-compiler $< --includedir vte-ng/bindings/gir -o $@

.PHONY: vte-ng

vte-ng/src/.libs/libvte-2.91.so: vte-ng

vte-ng:
	bash -c 'cd vte-ng; \
	./autogen.sh --disable-static --disable-vala --disable-gtk-doc-html --with-gnutls --without-iconv --disable-glade --enable-introspection'
	$(MAKE) -C vte-ng
