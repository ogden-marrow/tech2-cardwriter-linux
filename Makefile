SHELL := /bin/bash
VERSION := 1.0.0
PREFIX ?= /usr/local
DESTDIR ?=
PYTHON ?= python3
CURDIR := $(shell pwd)

BUILD := $(CURDIR)/build
DOWNLOADS := $(BUILD)/downloads
WINE_VERSION := 11.20
WINE_TARBALL := wine-$(WINE_VERSION)-amd64-wow64.tar.xz
WINE_URL := https://github.com/Kron4ek/Wine-Builds/releases/download/$(WINE_VERSION)/$(WINE_TARBALL)
WINE_SHA256 := 482a493c755dcea776199b86560e0fb0f969bb0275c67d88120b0b35b0df34b9

CARDWRITER_ZIP := cardwriter.zip
CARDWRITER_URL := https://web.archive.org/web/20220314094241id_/http://alexre.ru/galery/upload/%D0%A4%D0%B0%D0%B9%D0%BB%D1%8B/Tech2/cardwriter.zip
CARDWRITER_SHA256 := 9bd0708d70b5efcfe8485939b9035ab2b8ca63c8eec67ae056b03f547c5ded91

INSTALL_ROOT := $(DESTDIR)$(PREFIX)/lib/tech2-cardwriter
DEB_ROOT := $(BUILD)/deb/root
DEB_FILE := $(BUILD)/tech2-cardwriter_$(VERSION)_amd64.deb

.PHONY: all check fetch install install-bundled uninstall deb clean distclean run dev man

all: check

check:
	$(PYTHON) -m py_compile $(shell find src -name '*.py')
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
	desktop-file-validate data/tech2-cardwriter.desktop
	@if command -v man >/dev/null 2>&1 && [ -f man/tech2-cardwriter.1 ]; then \
		man --warnings -l man/tech2-cardwriter.1 >/dev/null; \
	fi

fetch: $(DOWNLOADS)/$(WINE_TARBALL) $(DOWNLOADS)/$(CARDWRITER_ZIP) $(BUILD)/wine/.stamp $(BUILD)/app/Card_writer.exe

$(DOWNLOADS)/$(WINE_TARBALL):
	@mkdir -p $(DOWNLOADS)
	curl -fL --retry 4 --retry-all-errors --connect-timeout 20 --max-time 900 -o $@.part $(WINE_URL)
	echo "$(WINE_SHA256)  $@.part" | sha256sum -c -
	mv $@.part $@

$(DOWNLOADS)/$(CARDWRITER_ZIP):
	@mkdir -p $(DOWNLOADS)
	curl -fL --retry 4 --retry-all-errors --connect-timeout 20 --max-time 120 -o $@.part $(CARDWRITER_URL)
	echo "$(CARDWRITER_SHA256)  $@.part" | sha256sum -c -
	mv $@.part $@

$(BUILD)/wine/.stamp: $(DOWNLOADS)/$(WINE_TARBALL)
	rm -rf $(BUILD)/wine
	mkdir -p $(BUILD)/wine
	tar -xf $< -C $(BUILD)/wine --strip-components=1
	touch $@

$(BUILD)/app/Card_writer.exe: $(DOWNLOADS)/$(CARDWRITER_ZIP)
	rm -rf $(BUILD)/app-tmp
	mkdir -p $(BUILD)/app-tmp $(BUILD)/app
	unzip -q -o $< -d $(BUILD)/app-tmp
	cp $(BUILD)/app-tmp/Card_writer.exe $(BUILD)/app/Card_writer.exe
	touch $@

install: fetch check
	install -d $(INSTALL_ROOT)/bin $(INSTALL_ROOT)/lib $(INSTALL_ROOT)/app
	cp -a src/tech2_cardwriter $(INSTALL_ROOT)/lib/
	find $(INSTALL_ROOT)/lib/tech2_cardwriter -type d -name __pycache__ -prune -exec rm -rf {} +
	chmod -R a+rX $(INSTALL_ROOT)/lib/tech2_cardwriter
	install -m 755 data/tech2-cardwriter $(INSTALL_ROOT)/bin/tech2-cardwriter
	install -m 755 $(BUILD)/app/Card_writer.exe $(INSTALL_ROOT)/app/Card_writer.exe
	install -d $(DESTDIR)$(PREFIX)/bin
	ln -sfn ../lib/tech2-cardwriter/bin/tech2-cardwriter $(DESTDIR)$(PREFIX)/bin/tech2-cardwriter
	install -d $(DESTDIR)$(PREFIX)/share/applications
	install -m 644 data/tech2-cardwriter.desktop $(DESTDIR)$(PREFIX)/share/applications/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
	install -m 644 data/tech2-cardwriter.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
	install -d $(DESTDIR)$(PREFIX)/share/metainfo
	install -m 644 data/com.github.ogdenmarrow.Tech2CardWriter.metainfo.xml $(DESTDIR)$(PREFIX)/share/metainfo/
	install -d $(DESTDIR)$(PREFIX)/share/man/man1
	@if [ -f man/tech2-cardwriter.1 ]; then \
		install -m 644 man/tech2-cardwriter.1 $(DESTDIR)$(PREFIX)/share/man/man1/; \
	fi
	install -d $(DESTDIR)$(PREFIX)/share/doc/tech2-cardwriter
	@if [ -f README.md ]; then install -m 644 README.md $(DESTDIR)$(PREFIX)/share/doc/tech2-cardwriter/; fi
	@if [ -f CHANGELOG.md ]; then install -m 644 CHANGELOG.md $(DESTDIR)$(PREFIX)/share/doc/tech2-cardwriter/; fi
	@if command -v wine >/dev/null 2>&1; then \
		echo "Using system Wine."; \
	else \
		echo "NOTE: Wine is not installed. Install it, or run: make install-bundled"; \
	fi

install-bundled: install
	rm -rf $(INSTALL_ROOT)/wine
	cp -a $(BUILD)/wine $(INSTALL_ROOT)/wine
	@echo "Bundled Wine installed under $(INSTALL_ROOT)/wine."

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/tech2-cardwriter
	rm -rf $(INSTALL_ROOT)
	rm -f $(DESTDIR)$(PREFIX)/share/applications/tech2-cardwriter.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/tech2-cardwriter.svg
	rm -f $(DESTDIR)$(PREFIX)/share/metainfo/com.github.ogdenmarrow.Tech2CardWriter.metainfo.xml
	rm -f $(DESTDIR)$(PREFIX)/share/man/man1/tech2-cardwriter.1
	rm -rf $(DESTDIR)$(PREFIX)/share/doc/tech2-cardwriter
	@echo "Removed the application. Your Wine prefix and images in ~/.local/share/tech2-cardwriter were left alone."

deb: fetch check
	rm -rf $(BUILD)/deb
	install -d $(DEB_ROOT)/opt/tech2-cardwriter/bin
	install -d $(DEB_ROOT)/opt/tech2-cardwriter/lib
	install -d $(DEB_ROOT)/opt/tech2-cardwriter/app
	install -d $(DEB_ROOT)/opt/tech2-cardwriter/share/icons/hicolor/scalable/apps
	install -d $(DEB_ROOT)/opt/tech2-cardwriter/share/metainfo
	install -d $(DEB_ROOT)/usr/bin
	install -d $(DEB_ROOT)/usr/share/applications
	install -d $(DEB_ROOT)/usr/share/icons/hicolor/scalable/apps
	install -d $(DEB_ROOT)/usr/share/metainfo
	install -d $(DEB_ROOT)/usr/share/man/man1
	install -d $(DEB_ROOT)/usr/share/doc/tech2-cardwriter
	install -d $(DEB_ROOT)/DEBIAN
	cp -a src/tech2_cardwriter $(DEB_ROOT)/opt/tech2-cardwriter/lib/
	find $(DEB_ROOT)/opt/tech2-cardwriter/lib/tech2_cardwriter -type d -name __pycache__ -prune -exec rm -rf {} +
	chmod -R a+rX $(DEB_ROOT)/opt/tech2-cardwriter/lib/tech2_cardwriter
	install -m 755 data/tech2-cardwriter $(DEB_ROOT)/opt/tech2-cardwriter/bin/tech2-cardwriter
	cp -a $(BUILD)/wine $(DEB_ROOT)/opt/tech2-cardwriter/wine
	install -m 755 $(BUILD)/app/Card_writer.exe $(DEB_ROOT)/opt/tech2-cardwriter/app/Card_writer.exe
	install -m 644 data/tech2-cardwriter.svg $(DEB_ROOT)/opt/tech2-cardwriter/share/icons/hicolor/scalable/apps/
	install -m 644 data/com.github.ogdenmarrow.Tech2CardWriter.metainfo.xml $(DEB_ROOT)/opt/tech2-cardwriter/share/metainfo/
	ln -sfn /opt/tech2-cardwriter/bin/tech2-cardwriter $(DEB_ROOT)/usr/bin/tech2-cardwriter
	install -m 644 data/tech2-cardwriter.desktop $(DEB_ROOT)/usr/share/applications/
	install -m 644 data/tech2-cardwriter.svg $(DEB_ROOT)/usr/share/icons/hicolor/scalable/apps/
	install -m 644 data/com.github.ogdenmarrow.Tech2CardWriter.metainfo.xml $(DEB_ROOT)/usr/share/metainfo/
	@if [ -f man/tech2-cardwriter.1 ]; then \
		install -m 644 man/tech2-cardwriter.1 $(DEB_ROOT)/usr/share/man/man1/tech2-cardwriter.1; \
		gzip -9n $(DEB_ROOT)/usr/share/man/man1/tech2-cardwriter.1; \
	fi
	@if [ -f README.md ]; then install -m 644 README.md $(DEB_ROOT)/usr/share/doc/tech2-cardwriter/; fi
	@if [ -f CHANGELOG.md ]; then install -m 644 CHANGELOG.md $(DEB_ROOT)/usr/share/doc/tech2-cardwriter/; fi
	install -m 644 debian/copyright $(DEB_ROOT)/usr/share/doc/tech2-cardwriter/copyright
	gzip -9n -c debian/changelog > $(DEB_ROOT)/usr/share/doc/tech2-cardwriter/changelog.Debian.gz
	chmod 644 $(DEB_ROOT)/usr/share/doc/tech2-cardwriter/changelog.Debian.gz
	sed "s/@INSTALLED_SIZE@/$$(du -sk $(DEB_ROOT) | cut -f1)/" debian/control > $(DEB_ROOT)/DEBIAN/control
	install -m 755 debian/postinst $(DEB_ROOT)/DEBIAN/postinst
	install -m 755 debian/prerm $(DEB_ROOT)/DEBIAN/prerm
	install -m 755 debian/postrm $(DEB_ROOT)/DEBIAN/postrm
	dpkg-deb --build --root-owner-group -Zxz $(DEB_ROOT) $(DEB_FILE)
	@echo "Built $(DEB_FILE)"

man:
	@if command -v man >/dev/null 2>&1; then man --warnings -l man/tech2-cardwriter.1 >/dev/null; fi

run: dev

dev: fetch
	rm -rf $(BUILD)/dev-root
	mkdir -p $(BUILD)/dev-root/bin $(BUILD)/dev-root/lib
	ln -s $(BUILD)/app $(BUILD)/dev-root/app
	ln -s $(BUILD)/wine $(BUILD)/dev-root/wine
	ln -s $(CURDIR)/src/tech2_cardwriter $(BUILD)/dev-root/lib/tech2_cardwriter
	ln -s $(CURDIR)/data/tech2-cardwriter $(BUILD)/dev-root/bin/tech2-cardwriter
	TECH2_CARDWRITER_ROOT=$(BUILD)/dev-root $(BUILD)/dev-root/bin/tech2-cardwriter

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -f $(BUILD)/*.deb
