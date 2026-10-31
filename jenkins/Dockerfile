FROM docker:29-cli AS docker_cli
FROM jenkins/jenkins:lts-jdk21

USER root
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker_cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose
COPY --from=docker_cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
USER jenkins
RUN jenkins-plugin-cli --plugins workflow-aggregator pipeline-model-definition git credentials-binding timestamper junit
