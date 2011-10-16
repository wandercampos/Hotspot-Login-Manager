#
# hotspot-login-manager
# https://github.com/syam44/Hotspot-Login-Manager
#
# Distributed under the GNU General Public License version 3
# https://www.gnu.org/copyleft/gpl.html
#
# Authors: syam (aks92@free.fr)
#
# Description: makefile for easier command-line interaction
#
# FIXME: declare generators/generated dependencies so we can get
#        rid of useless .PHONY directives and get a cleaner make chain.
#


#
# Display available targets
#
.PHONY: usage
usage:
	@echo "Targets:"
	@echo "    clean       Clean intermediary files."
	@echo "    i18n-pot    Generate messages.pot translation model."
	@echo "    i18n-mo     Generate .mo catalog files from existing .po translated files."
	@echo "    version     Spread version information from root \"VERSION\" file to the whole codebase."


#
# I18N: Generate messages.pot translation model
#
.PHONY: i18n-pot
i18n-pot:
	devtools/make-i18n-pot


#
# I18N: Generate .mo catalog files from existing .po translated files
#
.PHONY: i18n-mo
i18n-mo:
	devtools/make-i18n-mo


#
# Clean intermediary files
#
.PHONY: clean
clean:
	devtools/make-clean


#
# Spread version information from root "VERSION" file to the whole codebase
#
.PHONY: version
version:
	devtools/make-version
