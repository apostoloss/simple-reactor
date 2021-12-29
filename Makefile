init:
	pip install -r requirements.txt ;

virtualenv:
	python -m venv .venv ;

destroy_venv:
  ( \
    source deactivate; \
    rm -fr ./.venv; \
  )

dev:
  virtualenv
  source activate
  init
