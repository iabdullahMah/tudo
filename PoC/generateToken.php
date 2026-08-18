<?PHP

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

// Generate all possible tokens between lower and upper timestamp
$ts_lower = $argv[1];
$ts_upper = $argv[2];
for ($ts = $ts_lower; $ts < $ts_upper; $ts++) {
    print(generateToken($ts) . "\n");
}
