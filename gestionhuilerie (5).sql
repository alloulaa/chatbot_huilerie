-- phpMyAdmin SQL Dump
-- version 5.1.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1
-- Généré le : sam. 25 avr. 2026 à 18:45
-- Version du serveur : 10.4.22-MariaDB
-- Version de PHP : 8.1.2

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `gestionhuilerie`
--

-- --------------------------------------------------------

--
-- Structure de la table `administrateur`
--

CREATE TABLE `administrateur` (
  `id_utilisateur` bigint(20) NOT NULL,
  `entreprise_id_admin` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `administrateur`
--

INSERT INTO `administrateur` (`id_utilisateur`, `entreprise_id_admin`) VALUES
(1, 1);

-- --------------------------------------------------------

--
-- Structure de la table `analyse_laboratoire`
--

CREATE TABLE `analyse_laboratoire` (
  `id_analyse` bigint(20) NOT NULL,
  `acidite_huile_pourcent` double DEFAULT NULL,
  `date_analyse` varchar(255) DEFAULT NULL,
  `indice_peroxyde_meq_o2_kg` double DEFAULT NULL,
  `k232` double DEFAULT NULL,
  `k270` double DEFAULT NULL,
  `polyphenols_mg_kg` double DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `lot_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Structure de la table `campagne_olives`
--

CREATE TABLE `campagne_olives` (
  `id_campagne` bigint(20) NOT NULL,
  `annee` varchar(255) NOT NULL,
  `date_debut` varchar(255) DEFAULT NULL,
  `date_fin` varchar(255) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `campagne_olives`
--

INSERT INTO `campagne_olives` (`id_campagne`, `annee`, `date_debut`, `date_fin`, `reference`, `huilerie_id`) VALUES
(1, '2025-2026', '2025-11-01', '2026-02-28', 'CAMP2025', 1),
(2, '2023', '2023-10-01', '2024-01-31', 'CAM-2023-H1', 1),
(3, '2024', '2024-10-05', '2025-02-15', 'CAM-2024-H1', 1),
(4, '2023', '2023-10-10', '2024-01-20', 'CAM-2023-H2', 2),
(5, '2024', '2024-10-08', '2025-01-30', 'CAM-2024-H2', 2),
(6, '2024', '2024-11-01', '2025-02-01', 'CAM-2024-H3', 3);

-- --------------------------------------------------------

--
-- Structure de la table `employe`
--

CREATE TABLE `employe` (
  `id_employe` bigint(20) DEFAULT NULL,
  `id_utilisateur` bigint(20) NOT NULL,
  `huilerie_id_emp` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Structure de la table `entreprise`
--

CREATE TABLE `entreprise` (
  `id_entreprise` bigint(20) NOT NULL,
  `adresse` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `nom` varchar(255) DEFAULT NULL,
  `telephone` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `entreprise`
--

INSERT INTO `entreprise` (`id_entreprise`, `adresse`, `email`, `nom`, `telephone`) VALUES
(1, 'el kef', 'belweli@gmail.com', 'belweli', '22939025'),
(2, 'Sfax, Route Tunis km5', 'contact@oleaSfax.tn', 'Oléa Sfax', '74123456'),
(3, 'Sousse, Zone Industrielle', 'info@huileriesousse.tn', 'Huilerie Sousse', '73456789');

-- --------------------------------------------------------

--
-- Structure de la table `etape_production`
--

CREATE TABLE `etape_production` (
  `id_etape_production` bigint(20) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `ordre` int(11) NOT NULL,
  `guide_production_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `etape_production`
--

INSERT INTO `etape_production` (`id_etape_production`, `description`, `nom`, `ordre`, `guide_production_id`) VALUES
(1, 'Pesée et contrôle du lot entrant', 'Réception & Pesée', 1, 1),
(2, 'Lavage des olives à l\'eau claire', 'Lavage', 2, 1),
(3, 'Broyage des olives', 'Broyage', 3, 1),
(4, 'Malaxage de la pâte pendant 30 min', 'Malaxage', 4, 1),
(5, 'Centrifugation horizontale (2 phases)', 'Centrifugation', 5, 1),
(6, 'Filtration finale et mise en stockage', 'Filtration', 6, 1),
(7, 'Réception & Pesée', 'Réception & Pesée', 1, 2),
(8, 'Broyage sans lavage préalable', 'Broyage direct', 2, 2),
(9, 'Malaxage court 20 min', 'Malaxage', 3, 2),
(10, 'Centrifugation', 'Centrifugation', 4, 2),
(11, 'Pesée et contrôle du lot entrant', 'Réception & Pesée', 1, 1),
(12, 'Lavage des olives à l\'eau claire', 'Lavage', 2, 1),
(13, 'Broyage des olives', 'Broyage', 3, 1),
(14, 'Malaxage de la pâte pendant 30 min', 'Malaxage', 4, 1),
(15, 'Centrifugation horizontale (2 phases)', 'Centrifugation', 5, 1),
(16, 'Filtration finale et mise en stockage', 'Filtration', 6, 1),
(17, 'Réception & Pesée', 'Réception & Pesée', 1, 2),
(18, 'Broyage sans lavage préalable', 'Broyage direct', 2, 2),
(19, 'Malaxage court 20 min', 'Malaxage', 3, 2),
(20, 'Centrifugation', 'Centrifugation', 4, 2);

-- --------------------------------------------------------

--
-- Structure de la table `execution_production`
--

CREATE TABLE `execution_production` (
  `id_execution_production` bigint(20) NOT NULL,
  `controle_temperature` bit(1) DEFAULT NULL,
  `date_debut` varchar(255) DEFAULT NULL,
  `date_fin_prevue` varchar(255) DEFAULT NULL,
  `date_fin_reelle` varchar(255) DEFAULT NULL,
  `observations` varchar(255) DEFAULT NULL,
  `reference` varchar(255) NOT NULL,
  `rendement` double DEFAULT NULL,
  `statut` varchar(255) NOT NULL,
  `guide_production_id` bigint(20) NOT NULL,
  `lot_olives_id` bigint(20) NOT NULL,
  `machine_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `execution_production`
--

INSERT INTO `execution_production` (`id_execution_production`, `controle_temperature`, `date_debut`, `date_fin_prevue`, `date_fin_reelle`, `observations`, `reference`, `rendement`, `statut`, `guide_production_id`, `lot_olives_id`, `machine_id`) VALUES
(10, b'0', '2026-04-25', '2026-04-26', '2026-04-25', '', 'EXE-LO07-G1-M8-20260425154341287', 0, 'TERMINEE', 1, 7, 8);

-- --------------------------------------------------------

--
-- Structure de la table `guide_production`
--

CREATE TABLE `guide_production` (
  `id_guide_production` bigint(20) NOT NULL,
  `date_creation` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `guide_production`
--

INSERT INTO `guide_production` (`id_guide_production`, `date_creation`, `description`, `nom`, `reference`, `huilerie_id`) VALUES
(1, '2023-09-01', 'Guide standard pour huile extra-vierge', 'Guide Extra Vierge', 'GP-001', 1),
(2, '2023-09-15', 'Guide pour huile vierge courante', 'Guide Huile Vierge', 'GP-002', 1),
(3, '2023-09-20', 'Procédure production biologique certifiée', 'Guide Bio', 'GP-003', 2),
(4, '2024-08-10', 'Guide production haute performance industrielle', 'Guide Industriel', 'GP-004', 3);

-- --------------------------------------------------------

--
-- Structure de la table `huilerie`
--

CREATE TABLE `huilerie` (
  `id_huilerie` bigint(20) NOT NULL,
  `active` bit(1) DEFAULT NULL,
  `capacite_production` int(11) DEFAULT NULL,
  `certification` varchar(255) DEFAULT NULL,
  `localisation` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `type` varchar(255) DEFAULT NULL,
  `entreprise_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `huilerie`
--

INSERT INTO `huilerie` (`id_huilerie`, `active`, `capacite_production`, `certification`, `localisation`, `nom`, `type`, `entreprise_id`) VALUES
(1, b'0', 1000, 'iso2023', 'lkef', 'zitouneya', 'industrielle', 1),
(2, b'1', 500, 'BIO2022', 'Sfax', 'Moulin Sfax', 'semi-industrielle', 1),
(3, b'1', 800, 'ISO9001', 'Sousse', 'Moulin Sousse', 'industrielle', 3),
(4, b'0', 200, NULL, 'Nabeul', 'Moulin Artisanal', 'artisanale', 2);

-- --------------------------------------------------------

--
-- Structure de la table `lot_olives`
--

CREATE TABLE `lot_olives` (
  `id_lot` bigint(20) NOT NULL,
  `acidite_olives_pourcent` double DEFAULT NULL,
  `bon_pesee_pdf_path` varchar(255) DEFAULT NULL,
  `date_reception` varchar(255) DEFAULT NULL,
  `date_recolte` varchar(255) DEFAULT NULL,
  `duree_stockage_avant_broyage` int(11) DEFAULT NULL,
  `fournisseurcin` varchar(255) DEFAULT NULL,
  `fournisseur_nom` varchar(255) DEFAULT NULL,
  `humidite_pourcent` double DEFAULT NULL,
  `lavage_effectue` varchar(255) DEFAULT NULL,
  `maturite` varchar(255) DEFAULT NULL,
  `methode_recolte` varchar(255) DEFAULT NULL,
  `origine` varchar(255) DEFAULT NULL,
  `pesee` double DEFAULT NULL,
  `quantite_initiale` double DEFAULT NULL,
  `quantite_restante` double DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `region` varchar(255) DEFAULT NULL,
  `taux_feuilles_pourcent` double DEFAULT NULL,
  `temps_depuis_recolte_heures` int(11) DEFAULT NULL,
  `type_sol` varchar(255) DEFAULT NULL,
  `variete` varchar(255) DEFAULT NULL,
  `campagne_id` bigint(20) NOT NULL,
  `huilerie_id` bigint(20) DEFAULT NULL,
  `matiere_premiere_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `lot_olives`
--

INSERT INTO `lot_olives` (`id_lot`, `acidite_olives_pourcent`, `bon_pesee_pdf_path`, `date_reception`, `date_recolte`, `duree_stockage_avant_broyage`, `fournisseurcin`, `fournisseur_nom`, `humidite_pourcent`, `lavage_effectue`, `maturite`, `methode_recolte`, `origine`, `pesee`, `quantite_initiale`, `quantite_restante`, `reference`, `region`, `taux_feuilles_pourcent`, `temps_depuis_recolte_heures`, `type_sol`, `variete`, `campagne_id`, `huilerie_id`, `matiere_premiere_id`) VALUES
(7, 5, 'generated/bons-pesee/bon-pesee-LO07.pdf', '2026-04-25', '2026-04-25', 1, 'fffffff', 'ggggggggggggg', 5, 'Non', 'moyenne', 'manuelle', 'e', 1000, 1000, 0, 'LO07', 'Nord', 5, 5, 'argileux', 'Chetoui', 1, 1, 1),
(8, 5, 'generated/bons-pesee/bon-pesee-LO08.pdf', '2026-04-25', '2026-04-25', 1, 'z', 'z', 5, 'Non', 'z', 'manuelle', 'e', 17852, 17852, 17852, 'LO08', 'Nord', 5, 5, 'argileux', 'Chetoui', 1, 1, 1);

-- --------------------------------------------------------

--
-- Structure de la table `machine`
--

CREATE TABLE `machine` (
  `id_machine` bigint(20) NOT NULL,
  `capacite` int(11) DEFAULT NULL,
  `etat_machine` varchar(255) DEFAULT NULL,
  `nom_machine` varchar(255) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_machine` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) DEFAULT NULL,
  `matiere_premiere_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `machine`
--

INSERT INTO `machine` (`id_machine`, `capacite`, `etat_machine`, `nom_machine`, `reference`, `type_machine`, `huilerie_id`, `matiere_premiere_id`) VALUES
(7, 1000, 'EN_SERVICE', 'Broyeur Principal', 'MCH-001', 'presse', 1, 1),
(8, 800, 'SURVEILLANCE', 'Malaxeur A', 'MCH-002', '2_phase', 1, 1),
(9, 600, 'MAINTENANCE', 'Centrifugeuse 1', 'MCH-003', '3_phase', 1, 1),
(10, 500, 'operationnelle', 'Broyeur Sfax', 'MCH-004', 'press', 2, 2),
(11, 400, 'operationnelle', 'Malaxeur Sfax', 'MCH-005', '2_phase', 2, 2),
(12, 700, 'operationnelle', 'Centrifugeuse Sousse', 'MCH-006', '3_phase', 3, 3);

-- --------------------------------------------------------

--
-- Structure de la table `matiere_premiere`
--

CREATE TABLE `matiere_premiere` (
  `id_matiere_premiere` bigint(20) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) DEFAULT NULL,
  `reference` varchar(255) NOT NULL,
  `type` varchar(255) DEFAULT NULL,
  `unite_mesure` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `matiere_premiere`
--

INSERT INTO `matiere_premiere` (`id_matiere_premiere`, `description`, `nom`, `reference`, `type`, `unite_mesure`, `huilerie_id`) VALUES
(1, 'Olives récoltées de la région de Le Kef', 'Olives Le Kef', 'MP-001', 'Olive', 'kg', 1),
(2, 'Olives Chemlali de Sfax', 'Olives Chemlali', 'MP-002', 'Olive', 'kg', 2),
(3, 'Olives Chétoui du Nord', 'Olives Chétoui', 'MP-003', 'Olive', 'kg', 3),
(4, 'Olives Zarrazi de Sousse', 'Olives Zarrazi', 'MP-004', 'Olive', 'kg', 3);

-- --------------------------------------------------------

--
-- Structure de la table `module`
--

CREATE TABLE `module` (
  `id_module` bigint(20) NOT NULL,
  `nom` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `module`
--

INSERT INTO `module` (`id_module`, `nom`) VALUES
(3, 'CAMPAGNE_OLIVES'),
(12, 'COMPTES_PROFILS'),
(1, 'DASHBOARD'),
(10, 'DASHBOARD_ADMIN'),
(4, 'GUIDE_PRODUCTION'),
(11, 'HUILERIES'),
(9, 'LOTS_TRAÇABILITE'),
(5, 'MACHINES'),
(6, 'MATIERES_PREMIERES'),
(2, 'RECEPTION'),
(7, 'STOCK'),
(8, 'STOCK_MOUVEMENT');

-- --------------------------------------------------------

--
-- Structure de la table `parametre_etape`
--

CREATE TABLE `parametre_etape` (
  `id_parametre_etape` bigint(20) NOT NULL,
  `code_parametre` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `unite_mesure` varchar(255) DEFAULT NULL,
  `valeur_estime` varchar(255) DEFAULT NULL,
  `etape_production_id` bigint(20) NOT NULL,
  `execution_production_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Structure de la table `password_reset_tokens`
--

CREATE TABLE `password_reset_tokens` (
  `id` bigint(20) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  `token` varchar(255) NOT NULL,
  `used` bit(1) NOT NULL,
  `utilisateur_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Structure de la table `permission`
--

CREATE TABLE `permission` (
  `id_privilege` bigint(20) NOT NULL,
  `can_create` bit(1) NOT NULL,
  `can_delete` bit(1) NOT NULL,
  `can_executed` bit(1) NOT NULL,
  `can_read` bit(1) NOT NULL,
  `can_update` bit(1) NOT NULL,
  `date_creation` datetime(6) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `module_id` bigint(20) NOT NULL,
  `profil_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `permission`
--

INSERT INTO `permission` (`id_privilege`, `can_create`, `can_delete`, `can_executed`, `can_read`, `can_update`, `date_creation`, `description`, `module_id`, `profil_id`) VALUES
(1, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 1, 1),
(2, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 2, 1),
(3, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 3, 1),
(4, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 4, 1),
(5, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 5, 1),
(6, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 6, 1),
(7, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 7, 1),
(8, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 8, 1),
(9, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 9, 1),
(10, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 10, 1),
(11, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 11, 1),
(12, b'1', b'1', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 12, 1),
(13, b'0', b'0', b'0', b'1', b'0', '2026-04-24 14:25:25.000000', NULL, 1, 2),
(14, b'1', b'0', b'1', b'1', b'0', '2026-04-24 14:25:25.000000', NULL, 2, 2),
(15, b'1', b'0', b'0', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 3, 2),
(16, b'1', b'0', b'1', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 4, 2),
(17, b'0', b'0', b'0', b'1', b'0', '2026-04-24 14:25:25.000000', NULL, 5, 2),
(18, b'1', b'0', b'0', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 6, 2),
(19, b'1', b'0', b'0', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 7, 2),
(20, b'1', b'0', b'0', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 8, 2),
(21, b'1', b'0', b'0', b'1', b'1', '2026-04-24 14:25:25.000000', NULL, 9, 2),
(22, b'0', b'0', b'0', b'0', b'0', '2026-04-24 14:25:25.000000', NULL, 10, 2),
(23, b'0', b'0', b'0', b'0', b'0', '2026-04-24 14:25:25.000000', NULL, 11, 2),
(24, b'0', b'0', b'0', b'0', b'0', '2026-04-24 14:25:25.000000', NULL, 12, 2);

-- --------------------------------------------------------

--
-- Structure de la table `prediction`
--

CREATE TABLE `prediction` (
  `id_prediction` bigint(20) NOT NULL,
  `date_creation` varchar(255) NOT NULL,
  `mode_prediction` varchar(50) NOT NULL,
  `probabilite_qualite` double DEFAULT NULL,
  `qualite_predite` varchar(100) DEFAULT NULL,
  `quantite_huile_recalculee_litres` double DEFAULT NULL,
  `rendement_predit_pourcent` double DEFAULT NULL,
  `execution_production_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Structure de la table `produit_final`
--

CREATE TABLE `produit_final` (
  `id_produit` bigint(20) NOT NULL,
  `date_production` varchar(255) DEFAULT NULL,
  `nom_produit` varchar(255) DEFAULT NULL,
  `qualite` varchar(255) DEFAULT NULL,
  `quantite_produite` double DEFAULT NULL,
  `reference` varchar(255) NOT NULL,
  `execution_production_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `produit_final`
--

INSERT INTO `produit_final` (`id_produit`, `date_production`, `nom_produit`, `qualite`, `quantite_produite`, `reference`, `execution_production_id`) VALUES
(9, '2026-04-25', 'Huile Chetoui', NULL, 0, 'PF09', 10);

-- --------------------------------------------------------

--
-- Structure de la table `profil`
--

CREATE TABLE `profil` (
  `id_profil` bigint(20) NOT NULL,
  `date_creation` datetime(6) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `profil`
--

INSERT INTO `profil` (`id_profil`, `date_creation`, `description`, `nom`) VALUES
(1, '2026-04-24 14:25:25.000000', 'Acces total', 'ADMIN'),
(2, '2026-04-24 14:25:25.000000', 'Acces operations metier', 'RESPONSABLE_PRODUCTION');

-- --------------------------------------------------------

--
-- Structure de la table `refresh_tokens`
--

CREATE TABLE `refresh_tokens` (
  `id` bigint(20) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  `revoked` bit(1) NOT NULL,
  `token` varchar(255) NOT NULL,
  `utilisateur_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `refresh_tokens`
--

INSERT INTO `refresh_tokens` (`id`, `expires_at`, `revoked`, `token`, `utilisateur_id`) VALUES
(1, '2026-05-01 16:28:37.000000', b'0', '17920b1b-6f09-42e5-a0b5-823f9d022fe3', 1),
(2, '2026-05-01 16:32:42.000000', b'0', '21939abd-7cb6-43f9-ad4d-cbacc43b9e39', 1),
(3, '2026-05-01 16:40:14.000000', b'0', '434a80b9-d399-4ef1-a29e-4cf27847e9e9', 1),
(4, '2026-05-01 16:53:06.000000', b'0', 'b2656a42-07cb-47d8-bc2f-e7272f7cc940', 1),
(5, '2026-05-01 17:00:08.000000', b'0', '9a8422d1-eebe-4587-a700-376a77e773f6', 1),
(6, '2026-05-02 13:53:56.000000', b'0', 'ef50cba3-a34b-4f2f-b354-d9b147cd2a4a', 1);

-- --------------------------------------------------------

--
-- Structure de la table `stock`
--

CREATE TABLE `stock` (
  `id_stock` bigint(20) NOT NULL,
  `quantite_disponible` double DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_stock` varchar(255) DEFAULT NULL,
  `lot_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `stock`
--

INSERT INTO `stock` (`id_stock`, `quantite_disponible`, `reference`, `type_stock`, `lot_id`) VALUES
(7, 17852, 'ST07', 'Olive', 8);

-- --------------------------------------------------------

--
-- Structure de la table `stock_movement`
--

CREATE TABLE `stock_movement` (
  `id_stock_movement` bigint(20) NOT NULL,
  `commentaire` varchar(255) DEFAULT NULL,
  `date_mouvement` varchar(255) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_mouvement` enum('AJUSTEMENT','ENTREE','TRANSFERT') DEFAULT NULL,
  `lot_id` bigint(20) DEFAULT NULL,
  `stock_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `stock_movement`
--

INSERT INTO `stock_movement` (`id_stock_movement`, `commentaire`, `date_mouvement`, `reference`, `type_mouvement`, `lot_id`, `stock_id`) VALUES
(15, 'Arrivage lot LO07', '2026-04-25', 'MS15', 'ENTREE', 7, 7),
(16, 'Transfert automatique lors de l\'execution EXE-LO07-G1-M8-20260425154341287', '2026-04-25', 'MS16', 'TRANSFERT', 7, 7),
(17, 'Arrivage lot LO08', '2026-04-25', 'MS17', 'ENTREE', 8, 7);

-- --------------------------------------------------------

--
-- Structure de la table `utilisateur`
--

CREATE TABLE `utilisateur` (
  `id_utilisateur` bigint(20) NOT NULL,
  `actif` enum('ACTIF','INACTIF') NOT NULL,
  `email` varchar(255) NOT NULL,
  `email_verified` bit(1) NOT NULL,
  `mot_de_passe` varchar(255) NOT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `telephone` varchar(255) DEFAULT NULL,
  `verification_token` varchar(255) DEFAULT NULL,
  `verification_token_expires_at` datetime(6) DEFAULT NULL,
  `profil_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Déchargement des données de la table `utilisateur`
--

INSERT INTO `utilisateur` (`id_utilisateur`, `actif`, `email`, `email_verified`, `mot_de_passe`, `nom`, `prenom`, `telephone`, `verification_token`, `verification_token_expires_at`, `profil_id`) VALUES
(1, 'ACTIF', 'admin@default.com', b'1', '$2a$10$biqp4m1ugUkiahcpBMsuRO1sByaDs6J6GCsgbQe7gbdqEsExz.jaO', 'Admin', 'Système', NULL, 'a94e2a19-64ef-4408-9eb3-7fbc5c90a2bb', '2026-04-25 16:32:42.000000', 1);

-- --------------------------------------------------------

--
-- Structure de la table `valeur_reelle_parametre`
--

CREATE TABLE `valeur_reelle_parametre` (
  `id_valeur_reelle_parametre` bigint(20) NOT NULL,
  `valeur_reelle` varchar(255) DEFAULT NULL,
  `execution_production_id` bigint(20) NOT NULL,
  `parametre_etape_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vue_machines_probleme`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vue_machines_probleme` (
`nom_machine` varchar(255)
,`etat_machine` varchar(255)
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vue_production_totale`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vue_production_totale` (
`total_production` double
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vue_rendement`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vue_rendement` (
`rendement_moyen` double
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vue_stock_total`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vue_stock_total` (
`type_stock` varchar(255)
,`total_stock` double
);

-- --------------------------------------------------------

--
-- Structure de la vue `vue_machines_probleme`
--
DROP TABLE IF EXISTS `vue_machines_probleme`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vue_machines_probleme`  AS SELECT `machine`.`nom_machine` AS `nom_machine`, `machine`.`etat_machine` AS `etat_machine` FROM `machine` WHERE `machine`.`etat_machine` in ('Surveillance','Maintenance') ;

-- --------------------------------------------------------

--
-- Structure de la vue `vue_production_totale`
--
DROP TABLE IF EXISTS `vue_production_totale`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vue_production_totale`  AS SELECT sum(`produit_final`.`quantite_produite`) AS `total_production` FROM `produit_final` ;

-- --------------------------------------------------------

--
-- Structure de la vue `vue_rendement`
--
DROP TABLE IF EXISTS `vue_rendement`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vue_rendement`  AS SELECT avg(`execution_production`.`rendement`) AS `rendement_moyen` FROM `execution_production` ;

-- --------------------------------------------------------

--
-- Structure de la vue `vue_stock_total`
--
DROP TABLE IF EXISTS `vue_stock_total`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vue_stock_total`  AS SELECT `stock`.`type_stock` AS `type_stock`, sum(`stock`.`quantite_disponible`) AS `total_stock` FROM `stock` GROUP BY `stock`.`type_stock` ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `administrateur`
--
ALTER TABLE `administrateur`
  ADD PRIMARY KEY (`id_utilisateur`),
  ADD UNIQUE KEY `UK44tpalrodl9ytqk2c2n3deju1` (`entreprise_id_admin`);

--
-- Index pour la table `analyse_laboratoire`
--
ALTER TABLE `analyse_laboratoire`
  ADD PRIMARY KEY (`id_analyse`),
  ADD UNIQUE KEY `UKauftcdplhc9o41psn6750p1sx` (`lot_id`);

--
-- Index pour la table `campagne_olives`
--
ALTER TABLE `campagne_olives`
  ADD PRIMARY KEY (`id_campagne`),
  ADD UNIQUE KEY `UK9ty5pnudb88ddlxnkg67odakn` (`reference`),
  ADD KEY `FKs8t2iqfuwiums9vdl56spk7hy` (`huilerie_id`);

--
-- Index pour la table `employe`
--
ALTER TABLE `employe`
  ADD PRIMARY KEY (`id_utilisateur`),
  ADD KEY `FK24v5ii6k1yah62wr4t60axy3a` (`huilerie_id_emp`);

--
-- Index pour la table `entreprise`
--
ALTER TABLE `entreprise`
  ADD PRIMARY KEY (`id_entreprise`);

--
-- Index pour la table `etape_production`
--
ALTER TABLE `etape_production`
  ADD PRIMARY KEY (`id_etape_production`),
  ADD KEY `FKngcreaesaqqyx3hatkg732wao` (`guide_production_id`);

--
-- Index pour la table `execution_production`
--
ALTER TABLE `execution_production`
  ADD PRIMARY KEY (`id_execution_production`),
  ADD UNIQUE KEY `UKjvhjk2kg19xwqcw2y7mmjvyt2` (`reference`),
  ADD KEY `FKmeshbjvxaes4lyw7m9rawx1c8` (`guide_production_id`),
  ADD KEY `FK9fgw77gskwnvnob4fa4cub5x0` (`lot_olives_id`),
  ADD KEY `FKcsia5cjjxm9x2g2p9w0epo3k9` (`machine_id`);

--
-- Index pour la table `guide_production`
--
ALTER TABLE `guide_production`
  ADD PRIMARY KEY (`id_guide_production`),
  ADD UNIQUE KEY `UKdbuq3vdui95foprn92qp2ii1a` (`reference`),
  ADD KEY `FK19wxgw32srw4p5426w82wfemd` (`huilerie_id`);

--
-- Index pour la table `huilerie`
--
ALTER TABLE `huilerie`
  ADD PRIMARY KEY (`id_huilerie`),
  ADD UNIQUE KEY `uk_huilerie_nom` (`nom`),
  ADD KEY `FK6lxie70n87jisvfj9ga3j5fwf` (`entreprise_id`);

--
-- Index pour la table `lot_olives`
--
ALTER TABLE `lot_olives`
  ADD PRIMARY KEY (`id_lot`),
  ADD UNIQUE KEY `UKe12qqum22imabxjowbj5qylp0` (`reference`);

--
-- Index pour la table `machine`
--
ALTER TABLE `machine`
  ADD PRIMARY KEY (`id_machine`),
  ADD UNIQUE KEY `UKrwc4ysfgi3rc8nws96lianqyt` (`reference`),
  ADD KEY `FK7awy44m6t3cr5bieg6mcn7rj6` (`huilerie_id`),
  ADD KEY `FKb5kubivqi218xy92cwhqyg9vb` (`matiere_premiere_id`);

--
-- Index pour la table `matiere_premiere`
--
ALTER TABLE `matiere_premiere`
  ADD PRIMARY KEY (`id_matiere_premiere`),
  ADD UNIQUE KEY `UKi7g03id651f2rn7yicrvudnar` (`reference`);

--
-- Index pour la table `module`
--
ALTER TABLE `module`
  ADD PRIMARY KEY (`id_module`),
  ADD UNIQUE KEY `uk_module_nom` (`nom`);

--
-- Index pour la table `parametre_etape`
--
ALTER TABLE `parametre_etape`
  ADD PRIMARY KEY (`id_parametre_etape`),
  ADD KEY `FKn33lu4fe47o1yqh5rurykmyv5` (`etape_production_id`),
  ADD KEY `FKfmxtqh07h4fbq9683hj218be` (`execution_production_id`);

--
-- Index pour la table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `UK71lqwbwtklmljk3qlsugr1mig` (`token`),
  ADD KEY `idx_password_reset_tokens_utilisateur_id` (`utilisateur_id`);

--
-- Index pour la table `permission`
--
ALTER TABLE `permission`
  ADD PRIMARY KEY (`id_privilege`),
  ADD UNIQUE KEY `uk_permission_profil_module` (`profil_id`,`module_id`),
  ADD KEY `idx_permission_profil_id` (`profil_id`),
  ADD KEY `idx_permission_module_id` (`module_id`);

--
-- Index pour la table `prediction`
--
ALTER TABLE `prediction`
  ADD PRIMARY KEY (`id_prediction`),
  ADD KEY `FKj6tsqot6di22fojhgt55y7x0g` (`execution_production_id`);

--
-- Index pour la table `produit_final`
--
ALTER TABLE `produit_final`
  ADD PRIMARY KEY (`id_produit`),
  ADD UNIQUE KEY `UK7cdn25ccec1pdyh0c8ndvdewn` (`reference`),
  ADD KEY `FKq12xc6sk9sem5coy8jg2ygjjl` (`execution_production_id`);

--
-- Index pour la table `profil`
--
ALTER TABLE `profil`
  ADD PRIMARY KEY (`id_profil`),
  ADD UNIQUE KEY `uk_profil_nom` (`nom`);

--
-- Index pour la table `refresh_tokens`
--
ALTER TABLE `refresh_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `UKghpmfn23vmxfu3spu3lfg4r2d` (`token`),
  ADD KEY `idx_refresh_tokens_utilisateur_id` (`utilisateur_id`);

--
-- Index pour la table `stock`
--
ALTER TABLE `stock`
  ADD PRIMARY KEY (`id_stock`),
  ADD KEY `FKahn3gfs4jg4dh0cfjmmq66xtq` (`lot_id`);

--
-- Index pour la table `stock_movement`
--
ALTER TABLE `stock_movement`
  ADD PRIMARY KEY (`id_stock_movement`),
  ADD KEY `FKkd9a4774f6adw0i0q6xy4tgpv` (`lot_id`),
  ADD KEY `FKs3qeghgdh1ye5iecin4v9jsjk` (`stock_id`);

--
-- Index pour la table `utilisateur`
--
ALTER TABLE `utilisateur`
  ADD PRIMARY KEY (`id_utilisateur`),
  ADD UNIQUE KEY `UKrma38wvnqfaf66vvmi57c71lo` (`email`),
  ADD UNIQUE KEY `UKhtdd6m7831984elvqeip9u78a` (`verification_token`),
  ADD KEY `idx_utilisateur_id` (`id_utilisateur`),
  ADD KEY `FKssvnc79lcj8l1hwgm230fiuh7` (`profil_id`);

--
-- Index pour la table `valeur_reelle_parametre`
--
ALTER TABLE `valeur_reelle_parametre`
  ADD PRIMARY KEY (`id_valeur_reelle_parametre`),
  ADD KEY `FKaoim1v7qmeesyv3gjudk2d03` (`execution_production_id`),
  ADD KEY `FKix44cxx4m626tfiw4eqyjx89v` (`parametre_etape_id`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `analyse_laboratoire`
--
ALTER TABLE `analyse_laboratoire`
  MODIFY `id_analyse` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `campagne_olives`
--
ALTER TABLE `campagne_olives`
  MODIFY `id_campagne` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT pour la table `entreprise`
--
ALTER TABLE `entreprise`
  MODIFY `id_entreprise` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT pour la table `etape_production`
--
ALTER TABLE `etape_production`
  MODIFY `id_etape_production` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT pour la table `execution_production`
--
ALTER TABLE `execution_production`
  MODIFY `id_execution_production` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT pour la table `guide_production`
--
ALTER TABLE `guide_production`
  MODIFY `id_guide_production` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `huilerie`
--
ALTER TABLE `huilerie`
  MODIFY `id_huilerie` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `lot_olives`
--
ALTER TABLE `lot_olives`
  MODIFY `id_lot` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT pour la table `machine`
--
ALTER TABLE `machine`
  MODIFY `id_machine` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT pour la table `matiere_premiere`
--
ALTER TABLE `matiere_premiere`
  MODIFY `id_matiere_premiere` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `module`
--
ALTER TABLE `module`
  MODIFY `id_module` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT pour la table `parametre_etape`
--
ALTER TABLE `parametre_etape`
  MODIFY `id_parametre_etape` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT pour la table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `permission`
--
ALTER TABLE `permission`
  MODIFY `id_privilege` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT pour la table `prediction`
--
ALTER TABLE `prediction`
  MODIFY `id_prediction` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT pour la table `produit_final`
--
ALTER TABLE `produit_final`
  MODIFY `id_produit` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT pour la table `profil`
--
ALTER TABLE `profil`
  MODIFY `id_profil` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `refresh_tokens`
--
ALTER TABLE `refresh_tokens`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT pour la table `stock`
--
ALTER TABLE `stock`
  MODIFY `id_stock` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT pour la table `stock_movement`
--
ALTER TABLE `stock_movement`
  MODIFY `id_stock_movement` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT pour la table `utilisateur`
--
ALTER TABLE `utilisateur`
  MODIFY `id_utilisateur` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT pour la table `valeur_reelle_parametre`
--
ALTER TABLE `valeur_reelle_parametre`
  MODIFY `id_valeur_reelle_parametre` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=27;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `administrateur`
--
ALTER TABLE `administrateur`
  ADD CONSTRAINT `FKdib6ntq8vwh62bdimb3w32xki` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id_utilisateur`),
  ADD CONSTRAINT `FKggsidf5g9yf7t7ifpqec5k7sv` FOREIGN KEY (`entreprise_id_admin`) REFERENCES `entreprise` (`id_entreprise`);

--
-- Contraintes pour la table `analyse_laboratoire`
--
ALTER TABLE `analyse_laboratoire`
  ADD CONSTRAINT `FKgm49rmfni4udndy59c6ri40w7` FOREIGN KEY (`lot_id`) REFERENCES `lot_olives` (`id_lot`);

--
-- Contraintes pour la table `campagne_olives`
--
ALTER TABLE `campagne_olives`
  ADD CONSTRAINT `FKs8t2iqfuwiums9vdl56spk7hy` FOREIGN KEY (`huilerie_id`) REFERENCES `huilerie` (`id_huilerie`);

--
-- Contraintes pour la table `employe`
--
ALTER TABLE `employe`
  ADD CONSTRAINT `FK24v5ii6k1yah62wr4t60axy3a` FOREIGN KEY (`huilerie_id_emp`) REFERENCES `huilerie` (`id_huilerie`),
  ADD CONSTRAINT `FKejqi2vsm7p30774s5rkfnridf` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id_utilisateur`);

--
-- Contraintes pour la table `etape_production`
--
ALTER TABLE `etape_production`
  ADD CONSTRAINT `FKngcreaesaqqyx3hatkg732wao` FOREIGN KEY (`guide_production_id`) REFERENCES `guide_production` (`id_guide_production`);

--
-- Contraintes pour la table `execution_production`
--
ALTER TABLE `execution_production`
  ADD CONSTRAINT `FK9fgw77gskwnvnob4fa4cub5x0` FOREIGN KEY (`lot_olives_id`) REFERENCES `lot_olives` (`id_lot`),
  ADD CONSTRAINT `FKcsia5cjjxm9x2g2p9w0epo3k9` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`id_machine`),
  ADD CONSTRAINT `FKmeshbjvxaes4lyw7m9rawx1c8` FOREIGN KEY (`guide_production_id`) REFERENCES `guide_production` (`id_guide_production`);

--
-- Contraintes pour la table `guide_production`
--
ALTER TABLE `guide_production`
  ADD CONSTRAINT `FK19wxgw32srw4p5426w82wfemd` FOREIGN KEY (`huilerie_id`) REFERENCES `huilerie` (`id_huilerie`);

--
-- Contraintes pour la table `huilerie`
--
ALTER TABLE `huilerie`
  ADD CONSTRAINT `FK6lxie70n87jisvfj9ga3j5fwf` FOREIGN KEY (`entreprise_id`) REFERENCES `entreprise` (`id_entreprise`);

--
-- Contraintes pour la table `machine`
--
ALTER TABLE `machine`
  ADD CONSTRAINT `FK7awy44m6t3cr5bieg6mcn7rj6` FOREIGN KEY (`huilerie_id`) REFERENCES `huilerie` (`id_huilerie`),
  ADD CONSTRAINT `FKb5kubivqi218xy92cwhqyg9vb` FOREIGN KEY (`matiere_premiere_id`) REFERENCES `matiere_premiere` (`id_matiere_premiere`);

--
-- Contraintes pour la table `parametre_etape`
--
ALTER TABLE `parametre_etape`
  ADD CONSTRAINT `FKfmxtqh07h4fbq9683hj218be` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`),
  ADD CONSTRAINT `FKn33lu4fe47o1yqh5rurykmyv5` FOREIGN KEY (`etape_production_id`) REFERENCES `etape_production` (`id_etape_production`);

--
-- Contraintes pour la table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD CONSTRAINT `FKeibiibmif85i859utr8rl5vf` FOREIGN KEY (`utilisateur_id`) REFERENCES `utilisateur` (`id_utilisateur`);

--
-- Contraintes pour la table `permission`
--
ALTER TABLE `permission`
  ADD CONSTRAINT `FKrblidv8pvif32dp9fe2f0i9pp` FOREIGN KEY (`profil_id`) REFERENCES `profil` (`id_profil`),
  ADD CONSTRAINT `FKtnix0mh61fpm4o7cb7n3a5uj7` FOREIGN KEY (`module_id`) REFERENCES `module` (`id_module`);

--
-- Contraintes pour la table `prediction`
--
ALTER TABLE `prediction`
  ADD CONSTRAINT `FKj6tsqot6di22fojhgt55y7x0g` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`);

--
-- Contraintes pour la table `produit_final`
--
ALTER TABLE `produit_final`
  ADD CONSTRAINT `FKq12xc6sk9sem5coy8jg2ygjjl` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`);

--
-- Contraintes pour la table `refresh_tokens`
--
ALTER TABLE `refresh_tokens`
  ADD CONSTRAINT `FKq2qrsiqa8xfqkhsxr5tuqt9ai` FOREIGN KEY (`utilisateur_id`) REFERENCES `utilisateur` (`id_utilisateur`);

--
-- Contraintes pour la table `stock`
--
ALTER TABLE `stock`
  ADD CONSTRAINT `FKahn3gfs4jg4dh0cfjmmq66xtq` FOREIGN KEY (`lot_id`) REFERENCES `lot_olives` (`id_lot`);

--
-- Contraintes pour la table `stock_movement`
--
ALTER TABLE `stock_movement`
  ADD CONSTRAINT `FKkd9a4774f6adw0i0q6xy4tgpv` FOREIGN KEY (`lot_id`) REFERENCES `lot_olives` (`id_lot`),
  ADD CONSTRAINT `FKs3qeghgdh1ye5iecin4v9jsjk` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`id_stock`);

--
-- Contraintes pour la table `utilisateur`
--
ALTER TABLE `utilisateur`
  ADD CONSTRAINT `FKssvnc79lcj8l1hwgm230fiuh7` FOREIGN KEY (`profil_id`) REFERENCES `profil` (`id_profil`);

--
-- Contraintes pour la table `valeur_reelle_parametre`
--
ALTER TABLE `valeur_reelle_parametre`
  ADD CONSTRAINT `FKaoim1v7qmeesyv3gjudk2d03` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`),
  ADD CONSTRAINT `FKix44cxx4m626tfiw4eqyjx89v` FOREIGN KEY (`parametre_etape_id`) REFERENCES `parametre_etape` (`id_parametre_etape`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
