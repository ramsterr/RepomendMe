FROM pgvector/pgvector:pg16

ARG AGE_VERSION=1.5.0
ARG PG_MAJOR=16

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        flex \
        bison \
        git \
        postgresql-server-dev-${PG_MAJOR} \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch v${AGE_VERSION} https://github.com/apache/age.git /tmp/age \
    && cd /tmp/age \
    && make PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config USE_PGXS=1 \
    && make install PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config USE_PGXS=1 \
    && rm -rf /tmp/age
