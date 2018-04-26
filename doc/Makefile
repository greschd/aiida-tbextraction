# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    = -n
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = aiida-tbextraction
SOURCEDIR     = source
BUILDDIR      = build
TARGETDIR     = /home/greschd/programming/Z2Pack_website/web/aiida-plugins/aiida-tbextraction

.PHONY: all
all: html

# Put it first so that "make" without argument is like "make help".
.PHONY: help
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: view
view:
	xdg-open "$(BUILDDIR)"/html/index.html

move:
	-rm -r $(TARGETDIR)
	mv $(BUILDDIR)/html $(TARGETDIR)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
.PHONY: Makefile
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
