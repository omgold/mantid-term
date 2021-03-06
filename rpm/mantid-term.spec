Summary: keyboard-controllable terminal emulator
Name:    mantid-term
Version: __VERSION__
Release: 1%{?dist}
Packager: Oliver Mangold
URL: https://github.com/omgold/mantid-term/
Source0: %{name}-%{version}.tar.gz
License: GPL 2/3
Group: System

Autoreq: 0
Autoprov: 0
%define debug_package %{nil}

%if 0%{?rhel:1}
%define _buildutils /opt/rh/devtoolset-8
BuildRequires: devtoolset-8-gcc devtoolset-8-gcc-c++
%else
BuildRequires: gcc gcc-c++
%endif

Requires: gtk3 gnutls

%if 0%{?suse_version:1}
Requires: libpcre2-8-0
BuildRequires: libpcre2-8-0
%define python3_pkgversion 3
%else
Requires: pcre2
BuildRequires: pcre2
%endif

Requires: python%{python3_pkgversion}
Requires: python%{python3_pkgversion}-gobject gobject-introspection
Requires: python%{python3_pkgversion}-PyYAML python%{python3_pkgversion}-gobject
BuildRequires: gtk3 gtk3-devel gtk-doc gnutls gnutls-devel pcre2-devel
BuildRequires: gobject-introspection-devel
BuildRequires: libtool intltool scdoc pkgconfig sed
BuildRequires: python%{python3_pkgversion} python%{python3_pkgversion}-devel
BuildRequires: python%{python3_pkgversion}-gobject gobject-introspection
BuildRequires: python%{python3_pkgversion}-PyYAML python%{python3_pkgversion}-gobject

#==============================================================
%description
Mantid is a xterm-compatible terminal emulator based on Vte-ng, similar to termite with customizable keybindings and multiple tabs

%prep
%setup -c %{name}

%build
mkdir build
cd build
%if 0%{?_buildutils:1}
bash -c '. %{_buildutils}/enable && make %{?_smp_mflags} -C .. vte-ng'
%else
make -C .. %{?_smp_mflags} vte-ng
%endif
make -C .. %{?_smp_mflags}

%install
cd build
make -C .. install DESTDIR=%{buildroot}

#==============================================================

%files
%defattr(-,root,root)
/usr/bin/mantid
/usr/lib/mantid
%{python3_sitelib}/mantid
/usr/share/mantid
/usr/share/man/man1/mantid.*
/usr/share/applications/mantid.desktop

#==============================================================

%changelog
* Tue Sep 17 2019 Oliver Mangold -> 1.0.4
- transparent window background did not work, fixed (issue #1)
* Sun Sep 15 2019 Oliver Mangold -> 1.0.3
- option -d (working directory) did not work, fixed
* Thu Sep 05 2019 Oliver Mangold -> 1.0.2
- making scrollbar colors of inactive window same as for active one
- fixing doc: scrollbar-padding actually is scrollbar-background
* Tue Aug 06 2019 Oliver Mangold -> 1.0.1
- Adding comments to non-trivial keybindings in example
- Print warning and advice if config file is not found
* Fri Jul 26 2019 Oliver Mangold -> 1.0
- initial version
