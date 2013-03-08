<html>
<head>
<title>Ma page de traitement</title>
</head>
<body>
<?
// on teste la déclaration de nos variables
echo '<div>Mon premier script en PHP</div>';

if (isset($_GET['nom']) && isset($_GET['fonction'])) {
	// on affiche nos résultats
	echo '<div>Votre nom est '.$_GET['nom'].' et votre fonction est '.$_GET['fonction'].'</div>';
}
?>
</body>
</html>
