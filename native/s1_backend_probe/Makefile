SHELL := /bin/bash

CC := /usr/bin/cc
AR := /usr/bin/ar
ARFLAGS := rcD

SOURCE_DATE_EPOCH ?= $(shell git show -s --format=%ct HEAD)
export SOURCE_DATE_EPOCH
export LC_ALL := C
export LANG := C
export TZ := UTC

CPPFLAGS := \
	-D_GNU_SOURCE \
	-Iinclude

CFLAGS := \
	-std=c17 \
	-O2 \
	-g \
	-Wall \
	-Wextra \
	-Werror \
	-Wpedantic \
	-Wconversion \
	-Wshadow \
	-Werror=date-time \
	-fstack-protector-strong \
	-fPIE \
	-ffile-prefix-map=$(CURDIR)=. \
	-fdebug-prefix-map=$(CURDIR)=. \
	-fmacro-prefix-map=$(CURDIR)=.

LDFLAGS := \
	-pie \
	-Wl,-z,relro \
	-Wl,-z,now \
	-Wl,-z,noexecstack \
	-Wl,--build-id=sha1

BUILD_DIR := build
BINARY := $(BUILD_DIR)/pchsi-s1-backend-probe

SOURCES := \
	src/errors.c \
	src/main.c

OBJECTS := \
	$(BUILD_DIR)/errors.o \
	$(BUILD_DIR)/main.o

.PHONY: all clean unit print-config

all: $(BINARY)

$(BUILD_DIR):
	mkdir -p "$@"

$(BUILD_DIR)/errors.o: src/errors.c include/pchsi_s1/errors.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/main.o: src/main.c include/pchsi_s1/common.h include/pchsi_s1/errors.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c "$<" -o "$@"

$(BINARY): $(OBJECTS)
	$(CC) $(OBJECTS) $(LDFLAGS) -o "$@"

unit: all
	"$(BINARY)" --describe >/dev/null
	! "$(BINARY)" --execute >/dev/null 2>&1

print-config:
	@printf '%s\n' \
		"CC=$(CC)" \
		"CFLAGS=$(CFLAGS)" \
		"LDFLAGS=$(LDFLAGS)" \
		"SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH)"

clean:
	rm -rf "$(BUILD_DIR)"


# ---------------------------------------------------------------------------
# Task 12: compile-only adversarial payload objects
# ---------------------------------------------------------------------------

PROBE_PAYLOAD_BUILD_DIR := $(BUILD_DIR)/probe-payloads
PROBE_PAYLOAD_SOURCES := $(sort $(wildcard probes/*.c))
PROBE_PAYLOAD_OBJECTS := $(patsubst probes/%.c,$(PROBE_PAYLOAD_BUILD_DIR)/%.o,$(PROBE_PAYLOAD_SOURCES))

.PHONY: probe-payloads

probe-payloads: $(PROBE_PAYLOAD_OBJECTS)

$(PROBE_PAYLOAD_BUILD_DIR):
	mkdir -p "$@"

$(PROBE_PAYLOAD_BUILD_DIR)/%.o: probes/%.c include/pchsi_s1/probe_protocol.h | $(PROBE_PAYLOAD_BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c "$<" -o "$@"
