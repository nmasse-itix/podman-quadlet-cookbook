##
## Makefile for the vLLM + llmsnap cookbook
##

# vLLM quadlet is mapped to the 10032 user (vllm) and 10000 group (itix-svc)
PROJECT_UID = 10032
PROJECT_GID = 10000

# The vLLM *models* run *rootful*: they need the NVIDIA GPU through CDI
# (nvidia.com/gpu=all) and --security-opt label=disable, which require root
# privileges (similar to the samba and vsftpd cookbooks). llmsnap itself,
# however, runs as a dedicated *non-root* container (User=8100): it is a pure
# control plane that only starts/stops the model units over D-Bus (see
# llmsnap.container and other/base/install-tools.d/vllm-polkit.sh).

# - traefik: TLS termination (automatic Let's Encrypt certificate), API-key
#            authentication and the /v1 path allowlist in front of llmsnap
#            (see other/traefik/vllm.yaml).
DEPENDENCIES = traefik

# Add empty directory for AI models and llmsnap config
TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/vllm/models
TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/vllm/llmsnap

# Include common Makefile
include ../../scripts/common.mk

.PHONY: test

# vLLM runs as root
$(TARGET_CHROOT)/etc/quadlets/vllm/models:
	install -m 0755 -o root -g root -D -d $@

# But llmsnap runs as a dedicated non-root user
$(TARGET_CHROOT)/etc/quadlets/vllm/llmsnap:
	install -m 0700 -o $(PROJECT_UID) -g $(PROJECT_GID) -D -d $@

# All vLLM config files are owned by root
$(filter models/%.yaml, $(TARGET_CONFIG_FILES) $(TARGET_EXAMPLES_CONFIG_FILES)):
	install -o root -g root -m 0644 $< $@

##
## `make test` — smoke-test the chain and measure model start/swap times.
##
## Talks straight to llmsnap on the host loopback (127.0.0.1:8000), bypassing
## Traefik and its API key. llmsnap holds each /v1/chat/completions request until
## the target model is actually serving, so the request's wall-clock time IS the
## time llmsnap needed to bring the model up:
##   - COLD START: from every model unit stopped -> model serving. We stop all
##     vllm-model@*.service first (needs root, hence `test: pre-requisites`) so
##     the number is reproducible run to run.
##   - SWAP: request the other model while one is loaded. llmsnap's exclusive
##     group cold-swaps on CPU (stop previous unit, start next); on the GPU
##     config it is a sleep/wake instead (see SPECS.md), which this same
##     measurement captures transparently.
##
## The model list is discovered from llmsnap itself (GET /v1/models), so it stays
## in sync with config.yaml with no hard-coded names.
##

# llmsnap control-plane endpoint (host loopback; bypasses Traefik / API key).
test: LLMSNAP_URL ?= http://127.0.0.1:8000
# How long to wait for llmsnap to answer /v1/models before giving up.
test: TEST_READY_TIMEOUT ?= 60
# Per-request cap: a first-run cold start also pulls the image + downloads
# weights + loads slowly on CPU (matches llmsnap's healthCheckTimeout).
test: TEST_LOAD_TIMEOUT ?= 1800

test: pre-requisites
	@run() { echo "+ $$*" >&2; "$$@"; }; \
	set -Eeuo pipefail; \
	url="$(LLMSNAP_URL)"; \
	resp="$$(mktemp /tmp/vllm-test-resp-XXXXXX)"; \
	trap 'rm -f "$$resp"' EXIT; \
	echo "==> Waiting for llmsnap at $$url ..."; \
	deadline=$$(( $$(date +%s) + $(TEST_READY_TIMEOUT) )); \
	until curl -sSf -o /dev/null "$$url/v1/models"; do \
		if [ "$$(date +%s)" -ge "$$deadline" ]; then \
			echo "llmsnap did not become ready within $(TEST_READY_TIMEOUT)s" >&2; \
			exit 1; \
		fi; \
		sleep 2; \
	done; \
	models="$$(curl -sSf "$$url/v1/models" | yq -p=json '.data[].id')"; \
	if [ -z "$$models" ]; then echo "llmsnap exposes no models" >&2; exit 1; fi; \
	echo "llmsnap is ready; models: $$(echo $$models | tr '\n' ' ')"; \
	reset_models() { \
		local m; \
		for m in $$models; do run systemctl stop "vllm-model@$$m.service" || true; done; \
		sleep 5; \
	}; \
	timed_request() { \
		local m="$$1" start end code; \
		start="$$(date +%s.%N)"; \
		code="$$(curl -sS -o "$$resp" -w '%{http_code}' --max-time $(TEST_LOAD_TIMEOUT) \
			-X POST "$$url/v1/chat/completions" -H 'Content-Type: application/json' \
			-d "{\"model\":\"$$m\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":1}")"; \
		end="$$(date +%s.%N)"; \
		if [ "$$code" != "200" ]; then \
			echo "request for '$$m' failed (HTTP $$code):" >&2; cat "$$resp" >&2; echo >&2; \
			exit 1; \
		fi; \
		awk -v s="$$start" -v e="$$end" 'BEGIN { printf "%.1f", e - s }'; \
	}; \
	echo; echo "==> Cold start times (each measured from all models stopped)"; \
	for m in $$models; do \
		reset_models; \
		printf '  cold start  %-24s ' "$$m"; \
		echo "$$(timed_request "$$m")s"; \
	done; \
	echo; echo "==> Swap times (switch model while another is loaded)"; \
	reset_models; \
	first="$$(echo $$models | awk '{print $$1}')"; \
	echo "  (warming up $$first ...)"; timed_request "$$first" >/dev/null; \
	n="$$(echo $$models | wc -w)"; prev="$$first"; swaps=0; \
	for m in $$models $$models; do \
		[ "$$m" = "$$prev" ] && continue; \
		printf '  swap  %-16s -> %-16s ' "$$prev" "$$m"; \
		echo "$$(timed_request "$$m")s"; \
		prev="$$m"; swaps=$$((swaps + 1)); \
		[ "$$swaps" -ge "$$n" ] && break; \
	done; \
	echo; echo "All timing tests completed."
