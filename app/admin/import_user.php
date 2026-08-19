<?php
include('../includes/utils.php');
#AUTH: This section doesn't have any auth or authz check so anyone can reach it
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $userObj = $_POST['userobj'];
    #SOURCE: User input object without sanitize
    if ($userObj !== "") {
        $user = unserialize($userObj);
        #TAINT: User input used without any sanitization 
        include('../includes/db_connect.php');
        $ret = pg_prepare(
            $db,
            "importuser_query",
            "insert into users (username, password, description) values ($1, $2, $3)"
        );
        $ret = pg_execute($db, "importuser_query", array($user->username, $user->password, $user->description));
    }
}
header('location:/index.php');
die();
