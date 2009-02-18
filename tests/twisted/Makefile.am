TWISTED_TESTS = \
		connect/connect-success.py \
		connect/connect-success-ssl.py \
		connect/connect-fail.py \
		connect/connect-fail-ssl.py \
		connect/server-quit-ignore.py \
		connect/server-quit-noclose.py \
		connect/invalid-nick.py \
		channels/join-muc-channel.py \
		messages/message-order.py \
		messages/leading-space.py \
		messages/long-message-split.py \
		messages/room-contact-mixup.py \
		$(NULL)

TESTS =

TESTS_ENVIRONMENT = \
	PYTHONPATH=@abs_top_srcdir@/tests/twisted:@abs_top_builddir@/tests/twisted \
	IDLE_SSL_KEY=@abs_top_srcdir@/tests/twisted/tools/idletest.key \
	IDLE_SSL_CERT=@abs_top_srcdir@/tests/twisted/tools/idletest.cert

if WANT_TWISTED_TESTS

check-local: check-twisted

check-twisted:
	$(MAKE) -C tools
	rm -f tools/core
	rm -f tools/idle-testing.log
	sh $(srcdir)/tools/with-session-bus.sh --config-file=tools/tmp-session-bus.conf -- $(MAKE) check-TESTS \
		TESTS="$(TWISTED_TESTS)" \
		TESTS_ENVIRONMENT="$(TESTS_ENVIRONMENT) $(TEST_PYTHON)"
	@if test -e tools/core; then\
		echo "Core dump exists: tools/core";\
		exit 1;\
	fi

endif

EXTRA_DIST = \
	     $(TWISTED_TESTS) \
	     servicetest.py \
	     idletest.py \
	     constants.py \
	     $(NULL)

CLEANFILES = idle-[1-9]*.log *.pyc */*.pyc

SUBDIRS = tools