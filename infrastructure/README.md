En este fichero esta la informacion de despliegue y uso por entornos.

Los entornos sobre los que trabajaremos seran los siguientes
La localizacion base para la customizacion de servicios y aplicaciones por entorno esta en el repo anewhope en la ruta infrastructure/environments.
Se recuerda que la base de la customizacion global esta en el fichero .env que esta en la raiz del proyecto y sirve para seleccionar el entorno activo.

Listado de environments

- macbook
- dev
- pre
- pro

Nota importante: en cada carpeta environments estan los ficheros protegidos de las variables sensibles para cada entorno. Para el caso por ejemplo del entorno macbook que este definido actualmente en el fichero .env con esta variable y valor environment: macbook. La localizacion del fichero de variables protegidas denominado protected_values.py estara localizado en la ruta infrastructure/environments/macbook/protected_values.py.

Las variables publicas de cada entorno se almacenan en env.yaml dentro de la misma carpeta:
infrastructure/environments/<entorno>/env.yaml.

Exportador:
python infrastructure/export_env.py --environment macbook > /tmp/env_exports.sh

Formato envfile:
python infrastructure/export_env.py --environment macbook --format envfile > /tmp/.env.macbook

Las caracteristicas de las configuraciones necesarias actuales son.

Comunes a todos los entornos linux: (valido para dev,pre y pro): El planteamiento es unificar versiones de sistema operativo, con lo cual es comun en la propuesta de que en todos los servidores se use Oracle Linux 10, pero hay un caso que requiere algo un poco especifico y complejo. El entorno de virtualizacion ha de poder tener acceso a la GPU fisica en este caso de Nvidia del servidor real para el caso del servidor trainer y en este servidor se han de instalar los drivers de CUDA para poder canalizar el uso de ese recurso de computacion.Me habria gustado sacar la version de todo en un cluster de Kubernetes y en el configurar el soporte que hay en kubernetes para maquinas virtuales nativas para el caso del servidor trainer,pero he de tratar de ser realista con los tiempos de los cuales dispongo,  


macbook:Disponer de un equipo macbook con el stack tecnologico que permita instalar el software de terceros, los intepretes de python y go y la instalacion de dependecias de los mismo. En este despligue el equipo asumira los roles de los tres servidores el de frontend, el de backend y trainer.

dev: Disponer de una maquina fisica con recusos hardware necesarios para permitir emular los tres servidores el de frontend, el de backend y trainer. En mi caso elegi Virtualbox de Oracle, por el uso tan cotidiano que he visto que tiene y por que permitia algunas posibilidades de uso de la GPU.

pre:En mi caso elegi AWS de Amazon, por el conocimiento que tengo en ese proveedor de cloud computing y por las capacidades de los servicios especiales para necesidades de IA o disponibilidad con recursos hardware necesarios como para desplegar la instancia de trainer con recursos de GPU. Se requieren servicios que exceden de las versiones gratuitas y conlleva costes de uso estaticos y dinamicos por uso.

pro: Se tratara de dejar documentado cuales son los cambios que se han de hacer para replicar en entorno de PRE en PRO y las recomendaciones para un entorno de produccion. 

## Estructura de despliegue por servidores

Los docker-compose.yml por servidor viven en `infrastructure/servers`:

- `frontend/docker-compose.yml`: nginx + `5_web_frontend` + `6_web_backoffice` + `7_service_frontend`.
- `backend/docker-compose.yml`: `8_service_backend` + `3_backend` + `fmanagement` + `mariadb`.
- `trainer/docker-compose.yml`: `4_trainer` + `keras_service` (placeholder).
- `macbook/docker-compose.yml`: solo aplicaciones internas (sin MariaDB ni Keras dockerizados).

## Nginx

- Linux (dev/pre/pro): plantilla `infrastructure/servers/frontend/nginx/nginx.conf.template`
  para renderizar con variables por entorno en ansible.
- macbook: config local `infrastructure/servers/macbook/nginx/nginx.conf` para Homebrew.

## Ejecución por aplicación

Cada app en `src/apps/*` incluye:

- `run.sh` (ejecución interpretada/local).
- `docker_execution.sh` (build + run Docker, cargando `.env` y `env.yaml`).

## Keras y TensorFlow (trainer)

- macbook: entorno virtual `.env_trainer` con TensorFlow CPU y Keras 2.15.
- dev/pre/pro: TensorFlow con GPU (CUDA) en Oracle Linux 10.





Enlaces de interes.

GPU Passthrough on VirtualBox 
https://www.reddit.com/r/VFIO/comments/dlesd0/gpu_passthrough_on_virtualbox/?utm_source=xpromo&utm_medium=amp&utm_name=amp_comment_iterations&utm_term=control_1&utm_content=post_body