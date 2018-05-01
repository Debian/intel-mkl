.PHONY: default

BIN= catalog testdgemm

default: $(BIN)

%: %.cc
	g++ $@.cc -o $@ $(shell pkg-config --libs --cflags mkl-rt)

clean:
	-$(RM) $(BIN)
