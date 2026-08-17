FROM php:8.4-apache

# Install PgSQL extension
RUN apt-get -q update && apt-get install -q -y libpq-dev && \
    docker-php-ext-install pgsql

# Install Xdebug from source (PECL channel is down; Debian trixie has no php8.4-xdebug package)
RUN apt-get -q update && apt-get install -q -y git $PHPIZE_DEPS && \
    git clone --depth 1 https://github.com/xdebug/xdebug.git /usr/src/xdebug && \
    cd /usr/src/xdebug && phpize && ./configure && make && make install && \
    docker-php-ext-enable xdebug && \
    rm -rf /usr/src/xdebug

# Configure PHP.ini for debugging
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY docker/app/xdebug.ini /tmp
RUN mv /tmp/xdebug.ini "$PHP_INI_DIR/conf.d/99-xdebug.ini"

# Add .phar extension to Apache config
RUN echo "AddType application/x-httpd-php .phar" >> /etc/apache2/apache2.conf

# Copy files over and set permissions
COPY app /var/www/html
RUN chown -R www-data:www-data /var/www/html
