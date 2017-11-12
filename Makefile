SUBDIR=src/computation

all: $(SUBDIR)

$(SUBDIR):
	$(MAKE) -C $@
	cp $(SUBDIR)/nfa_error .
	cp $(SUBDIR)/label_nfa .

clean:
	rm -f nfa_error
	$(MAKE) -C $(SUBDIR) clean

no-data:
	rm -f *.fa *.dot *.jpg *.json *.jsn

.PHONY: all clean $(SUBDIR)
