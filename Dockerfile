FROM public.ecr.aws/lambda/python:3.12 AS build

RUN dnf install -y git make zip && dnf clean all

WORKDIR /build
COPY . .

# Use the same build rules and dependencies as the Makefile.
RUN make default \
    && PYTHONPATH=sbn-sis.zip:src/python/lib/python3.12/site-packages \
       python3.12 -c "import lambda_function"

# Export only the two deployment files to the host.
FROM scratch AS artifacts
COPY --from=build /build/sbn-sis.zip /sbn-sis.zip
COPY --from=build /build/sbn-sis-dependencies.zip /sbn-sis-dependencies.zip
