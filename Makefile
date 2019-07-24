all: libmantid.so Mantid-1.0.typelib mantid.1

libmantid.so: libmantid.c
	gcc -O2 -I vte-ng/src/ `pkg-config --cflags gtk+-3.0` -shared -fpic $< -o $@

Mantid-1.0.typelib: Mantid-1.0.gir
	g-ir-compiler $< --includedir vte-ng/bindings/gir -o $@

.PHONY: vte-ng

mantid.1: mantid/*.py
	./gen-man

vte-ng/src/.libs/libvte-2.91.so: vte-ng

vte-ng:
	bash -c 'cd vte-ng; \
	./autogen.sh --disable-static --disable-vala --disable-gtk-doc-html --with-gnutls --without-iconv --disable-glade --enable-introspection --prefix=/usr/lib/mantid'
	$(MAKE) -C vte-ng

install:
	install -m 755 -d ${DESTDIR}/usr/bin \
                    ${DESTDIR}/usr/lib/mantid \
                    ${DESTDIR}/usr/share/man/man1
	install -m 755 mantid-py ${DESTDIR}/usr/lib/mantid/mantid
	install -m 755 mantid-py ${DESTDIR}/usr/bin
	ln -sf ../lib/mantid/mantid ${DESTDIR}/usr/bin/mantid
	$(MAKE) -C vte-ng install DESTDIR=${DESTDIR}
	install -m 644 Mantid-1.0.typelib ${DESTDIR}/usr/lib/mantid/lib/girepository-1.0
	install -m 644 Mantid-1.0.gir ${DESTDIR}/usr/lib/mantid/share/gir-1.0
	install -m 755 -d ${DESTDIR}/`./get-python-dir`/mantid
	install -m 644 mantid/*.py ${DESTDIR}/`./get-python-dir`/mantid
	install -m 755 libmantid.so ${DESTDIR}/usr/lib/mantid/lib
	install -m 755 -d ${DESTDIR}/usr/share/mantid
	install -m 644 config/mantid.yml ${DESTDIR}/usr/share/mantid
	install -m 644 mantid.1 ${DESTDIR}/usr/share/man/man1
	python3 -O -m compileall -d `./get-python-dir`/mantid ${DESTDIR}/`./get-python-dir`/mantid
