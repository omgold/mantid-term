.PHONY: all clean

GIT_REF ?= master

all: override \
	OP ?= package

all:
	${MAKE} ${foreach d,${DISTROS},${d}.distro-all} OP=${OP} CONTAINER=${CONTAINER}

%.distro-all: private \
	SPEC = ${patsubst %.distro-all,%,$@}
%.distro-all: private \
	IMAGE_AND_DISTRO = ${basename ${SPEC}}
%.distro-all: export \
	PACKAGE_TYPE = ${patsubst .%,%,${suffix ${SPEC}}}
%.distro-all: export \
	IMAGE_NAME = ${basename ${IMAGE_AND_DISTRO}}
%.distro-all: export \
	DISTRO = ${patsubst .%,%,${suffix ${IMAGE_AND_DISTRO}}}

%.distro-all:
	${MAKE} ${OP} CONTAINER=${CONTAINER}

clean:
	[ -z "${shell sudo docker container ls -a -q --filter=name=${DISTRO}.${CONTAINER} }" ] || { \
	    sudo docker container stop ${DISTRO}.${CONTAINER}; \
	    sudo docker container rm ${DISTRO}.${CONTAINER}; \
	}

container: clean
	sudo docker image pull ${IMAGE_NAME}
	sudo docker container create -i -t --name ${DISTRO}.${CONTAINER} ${IMAGE_NAME} bash -i

prepare:
	sudo docker container start ${DISTRO}.${CONTAINER}
	sudo docker container exec ${DISTRO}.${CONTAINER} bash -e -c ' \
	case ${PACKAGE_TYPE} in \
	rpm) \
	    case ${DISTRO} in \
	    fedora) \
	        dnf -y install make git python3-devel rpm-build dnf-plugins-core; \
	        ;; \
	    centos) \
	        yum -y install epel-release centos-release-scl make git python36-devel rpm-build yum-utils; \
	        ;; \
	    opensuse) \
	        zypper --non-interactive install make git python3-devel rpm-build; \
	        ;; \
        esac \
	    ;; \
	deb) \
	    apt-get update; \
	    apt-get install --assume-yes git devscripts equivs python3-distutils; \
	    ;; \
	arch) \
	    pacman -Suy --noconfirm; \
	    pacman -S --needed --noconfirm base-devel git; \
	esac; \
	useradd -m build || :; \
    '
	sudo docker container exec -u build -w /home/build ${DISTRO}.${CONTAINER} bash -ex -c ' \
	rm -rf mantid-term; \
	git clone https://github.com/omgold/mantid-term; \
	cd mantid-term; \
	git checkout ${GIT_REF}; \
	git submodule init; \
	git submodule update; \
	rm -rf debbuild; \
	case ${PACKAGE_TYPE} in \
	rpm) \
	    case ${DISTRO} in \
	    opensuse) \
	        make srpm; \
	        ;; \
	    esac \
	    ;; \
	deb) \
	    make deb-build-deps; \
	    ;; \
	esac \
	';
	sudo docker container exec ${DISTRO}.${CONTAINER} bash -ex -c ' \
	cd /home/build/mantid-term; \
	case ${PACKAGE_TYPE} in \
	rpm) \
	    case ${DISTRO} in \
	    fedora) \
	        dnf builddep -y rpm/mantid-term.spec; \
	        ;; \
	    centos) \
	        yum-builddep -y rpm/mantid-term.spec; \
	        ;; \
	    opensuse) \
	        VERSION=$$(cat VERSION); \
	        zypper --non-interactive -p http://download.opensuse.org/tumbleweed/repo/oss/ install scdoc; \
	        zypper --non-interactive si -d /home/build/rpmbuild/SRPMS/mantid-term-$$VERSION-*.src.rpm; \
	        ;; \
	    esac \
	    ;; \
	deb) \
	    VERSION=$$(cat VERSION); \
	    apt-get install --assume-yes ./debbuild/mantid-term_$$VERSION/mantid-term-build-deps_$$VERSION-*_all.deb; \
	    ;; \
	arch) \
	    pacman -S --needed --noconfirm $$(su -s /bin/bash build -c '\''. archpkg/PKGBUILD; echo "$${depends[@]}" "$${makedepends[@]}"'\''); \
	    ;; \
	esac; \
    '

.PHONY: build

build:
	sudo docker container exec -u build -w /home/build ${DISTRO}.${CONTAINER} bash -ex -c ' \
	cd mantid-term; \
	case ${PACKAGE_TYPE} in \
	rpm) \
	    make rpm; \
	    ;; \
	deb) \
	    make srcdeb; \
	    make deb; \
	    ;; \
	arch) \
	    make archpkg; \
	esac; \
	'

.PHONY: export

export:
	rm -rf export/${DISTRO}
	mkdir -p export/${DISTRO}
	case ${PACKAGE_TYPE} in \
	rpm) \
		sudo docker container exec -u build -w /home/build ${DISTRO}.${CONTAINER} bash -ex -c ' \
	    VERSION=$$(cat mantid-term/VERSION); \
	    cd rpmbuild; \
	    tar -cv {SRPMS,RPMS/*}/mantid-term-$$VERSION-1.*.rpm; \
	    ' \
	    ;; \
	deb) \
		sudo docker container exec -u build -w /home/build ${DISTRO}.${CONTAINER} bash -ex -c ' \
	    VERSION=$$(cat mantid-term/VERSION); \
	    cd mantid-term/debbuild; \
	    tar -cv mantid-term_$$VERSION{-1_*.deb,.orig.tar.gz,-1.debian.tar.*}; \
	    ' \
	    ;; \
	arch) \
		sudo docker container exec -u build -w /home/build ${DISTRO}.${CONTAINER} bash -ex -c ' \
	    VERSION=$$(cat mantid-term/VERSION); \
	    cd mantid-term/archbuild; \
	    tar -cv mantid-term-$$VERSION-1-*.pkg.tar.*; \
	    ' \
	    ;; \
	esac | tar -x -C export/${DISTRO}

package:
	${MAKE} container
	${MAKE} prepare
	${MAKE} build
	${MAKE} export
