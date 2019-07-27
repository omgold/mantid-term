Summary: keyboard-controllable terminal emulator
Name:    mantid-term
Version: 1.0.0
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

Requires: gtk3 gnutls pcre2
Requires: python%{python3_pkgversion}
Requires: python%{python3_pkgversion}-gobject gobject-introspection
Requires: python%{python3_pkgversion}-PyYAML python%{python3_pkgversion}-gobject
BuildRequires: gtk3 gtk3-devel gtk-doc gnutls gnutls-devel pcre2 pcre2-devel
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
* Fri Jul 26 2019 NEC HPCE OM -> 1.0
- initial version
