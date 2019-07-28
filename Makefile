CC ?= gcc
CXX ?= g++

SOURCE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
BUILD_DIR ?= $(realpath ${PWD})/
PYTHON_LIB_DIR := $(shell ${SOURCE_DIR}/get-python-dir)
RPM_NAME := $(shell rpm -q --qf %{NAME}-%{VERSION} --specfile rpm/mantid.spec)
RPM_NAME_RELEASE := $(shell rpm -q --qf %{NAME}-%{VERSION}-%{RELEASE} --specfile rpm/mantid.spec)

all: ${BUILD_DIR}/libmantid.so ${BUILD_DIR}/Mantid-1.0.typelib ${BUILD_DIR}/mantid.1

.PHONY: rpm srpm

rpm: srpm
	rpmbuild --rebuild ${HOME}/rpmbuild/SRPMS/${RPM_NAME_RELEASE}.src.rpm

srpm:
	mkdir -p ${HOME}/rpmbuild/SOURCES
	tar --exclude=.git --exclude-caches-all -zcvf ${HOME}/rpmbuild/SOURCES/${RPM_NAME}.tar.gz .
	rpmbuild -bs rpm/mantid.spec

${BUILD_DIR}/libmantid.so: libmantid.c ${BUILD_DIR}/CACHEDIR.TAG
	${CC} -O2 -std=c99 -I ${BUILD_DIR}/vte-ng/src/ `pkg-config --cflags gtk+-3.0` -shared -fpic $< -o $@

${BUILD_DIR}/Mantid-1.0.typelib: Mantid-1.0.gir ${BUILD_DIR}/CACHEDIR.TAG
	g-ir-compiler $< --includedir ${BUILD_DIR}/vte-ng/bindings/gir -o $@

.PHONY: vte-ng

${BUILD_DIR}/mantid.1: mantid/*.py ${BUILD_DIR}/Mantid-1.0.typelib ${BUILD_DIR}/libmantid.so
	cd ${BUILD_DIR} && ${SOURCE_DIR}/gen-man

${SOURCE_DIR}/vte-ng/configure:
	NOCONFIGURE=1 ${SOURCE_DIR}/vte-ng/autogen.sh

${BUILD_DIR}/vte-ng/Makefile: ${BUILD_DIR}/CACHEDIR.TAG ${SOURCE_DIR}/vte-ng/configure
	mkdir -p ${BUILD_DIR}/vte-ng
	cd ${BUILD_DIR}/vte-ng && \
	CC=${CC} CXX=${CXX} ${SOURCE_DIR}/vte-ng/configure --disable-static --disable-vala --disable-gtk-doc-html --with-gnutls --without-iconv --disable-glade --enable-introspection --prefix=/usr/lib/mantid

vte-ng: ${BUILD_DIR}/vte-ng/Makefile ${BUILD_DIR}/CACHEDIR.TAG
	$(MAKE) -C ${BUILD_DIR}/vte-ng
	cp ${SOURCE_DIR}/vte-ng/src/vte/*.h ${BUILD_DIR}/vte-ng/src/vte/

${BUILD_DIR}/CACHEDIR.TAG:
	if [ "${SOURCE_DIR}" = "${BUILD_DIR}" ]; then \
	    echo "refusing to build in source tree"; \
	    exit 1; \
	fi
	echo 'Signature: 8a477f597d28d172789f06886806bc55' >${BUILD_DIR}/CACHEDIR.TAG

install:
	if [ -z ${PYTHON_LIB_DIR} ]; then \
		echo "cannot determine python install dir"; \
	    exit 1; \
    fi
	install -m 755 -d ${DESTDIR}/usr/bin \
                    ${DESTDIR}/usr/lib/mantid \
                    ${DESTDIR}/usr/share/man/man1
	install -m 755 mantid-py ${DESTDIR}/usr/lib/mantid/mantid
	ln -sf ../lib/mantid/mantid ${DESTDIR}/usr/bin/mantid
	$(MAKE) -C ${BUILD_DIR}/vte-ng install DESTDIR=${DESTDIR}
	install -m 644 ${BUILD_DIR}/Mantid-1.0.typelib ${DESTDIR}/usr/lib/mantid/lib/girepository-1.0
	install -m 644 Mantid-1.0.gir ${DESTDIR}/usr/lib/mantid/share/gir-1.0
	install -m 755 -d ${DESTDIR}/${PYTHON_LIB_DIR}/mantid
	install -m 644 mantid/*.py ${DESTDIR}/${PYTHON_LIB_DIR}/mantid
	install -m 755 ${BUILD_DIR}/libmantid.so ${DESTDIR}/usr/lib/mantid/lib
	install -m 755 -d ${DESTDIR}/usr/share/mantid
	install -m 644 config/mantid*.yml ${DESTDIR}/usr/share/mantid
	install -m 644 ${BUILD_DIR}/mantid.1 ${DESTDIR}/usr/share/man/man1
	install -m 755 -d ${DESTDIR}/usr/share/applications
	install -m 644 mantid.desktop ${DESTDIR}/usr/share/applications
	python3 -O -m compileall -d ${PYTHON_LIB_DIR}/mantid ${DESTDIR}/${PYTHON_LIB_DIR}/mantid
