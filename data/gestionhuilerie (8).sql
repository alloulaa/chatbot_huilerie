-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: May 06, 2026 at 06:29 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `gestionhuilerie`
--

-- --------------------------------------------------------

--
-- Table structure for table `administrateur`
--

CREATE TABLE `administrateur` (
  `id_utilisateur` bigint(20) NOT NULL,
  `entreprise_id_admin` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `administrateur`
--

INSERT INTO `administrateur` (`id_utilisateur`, `entreprise_id_admin`) VALUES
(1, 1);

-- --------------------------------------------------------

--
-- Table structure for table `analyse_laboratoire`
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `analyse_laboratoire`
--

INSERT INTO `analyse_laboratoire` (`id_analyse`, `acidite_huile_pourcent`, `date_analyse`, `indice_peroxyde_meq_o2_kg`, `k232`, `k270`, `polyphenols_mg_kg`, `reference`, `lot_id`) VALUES
(1, 0.6, '2026-05-04', 8, 1.9, 0.18, 50, 'AL01', 1);

-- --------------------------------------------------------

--
-- Table structure for table `campagne_olives`
--

CREATE TABLE `campagne_olives` (
  `id_campagne` bigint(20) NOT NULL,
  `annee` varchar(255) NOT NULL,
  `date_debut` varchar(255) DEFAULT NULL,
  `date_fin` varchar(255) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `campagne_olives`
--

INSERT INTO `campagne_olives` (`id_campagne`, `annee`, `date_debut`, `date_fin`, `reference`, `huilerie_id`) VALUES
(1, '2026', '2026-11-12', '2027-01-12', 'CP01', 1),
(2, '2025', '2025-11-13', '2026-01-14', 'CP02', 2),
(3, '2025', '2025-11-11', '2026-01-12', 'CP03', 1),
(4, '2026', '2026-11-12', '2027-01-13', 'CP04', 2);

-- --------------------------------------------------------

--
-- Table structure for table `employe`
--

CREATE TABLE `employe` (
  `id_employe` bigint(20) DEFAULT NULL,
  `id_utilisateur` bigint(20) NOT NULL,
  `huilerie_id_emp` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `entreprise`
--

CREATE TABLE `entreprise` (
  `id_entreprise` bigint(20) NOT NULL,
  `adresse` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `nom` varchar(255) DEFAULT NULL,
  `telephone` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `entreprise`
--

INSERT INTO `entreprise` (`id_entreprise`, `adresse`, `email`, `nom`, `telephone`) VALUES
(1, 'manouba', '4ina@gmail.com', '4ina', '52630458');

-- --------------------------------------------------------

--
-- Table structure for table `etape_production`
--

CREATE TABLE `etape_production` (
  `id_etape_production` bigint(20) NOT NULL,
  `code_etape` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `ordre` int(11) NOT NULL,
  `guide_production_id` bigint(20) NOT NULL,
  `machine_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `etape_production`
--

INSERT INTO `etape_production` (`id_etape_production`, `code_etape`, `description`, `nom`, `ordre`, `guide_production_id`, `machine_id`) VALUES
(1, 'reception', 'Réception des olives et contrôle initial de la matière première.', 'Réception', 1, 1, NULL),
(2, 'nettoyage_lavage', 'Nettoyage et lavage des olives avant transformation.', 'Nettoyage / Lavage', 2, 1, 5),
(3, 'broyage', 'Broyage de la matière première avant malaxage.', 'Broyage', 3, 1, 1),
(4, 'malaxage', 'Homogénéisation de la pâte avec contrôle de température et durée.', 'Malaxage', 4, 1, 2),
(5, 'ajout_eau', 'Ajout d\'eau nécessaire au procédé 3 phases.', 'Ajout d\'eau', 5, 1, 6),
(6, 'decanteur_3_phases_separateur', 'Extraction et séparation par décanteur 3 phases suivi d\'un séparateur vertical.', 'Décanteur 3 phases + Séparateur vertical', 6, 1, 4),
(7, 'stockage', 'Stockage de l\'huile obtenue dans des conditions adaptées.', 'Stockage', 7, 1, 7);

-- --------------------------------------------------------

--
-- Table structure for table `execution_production`
--

CREATE TABLE `execution_production` (
  `id_execution_production` bigint(20) NOT NULL,
  `controle_temperature` bit(1) DEFAULT NULL,
  `date_debut` varchar(255) DEFAULT NULL,
  `date_fin_prevue` varchar(255) DEFAULT NULL,
  `date_fin_reelle` varchar(255) DEFAULT NULL,
  `observations` varchar(255) DEFAULT NULL,
  `reference` varchar(255) NOT NULL,
  `statut` varchar(255) NOT NULL,
  `guide_production_id` bigint(20) NOT NULL,
  `lot_olives_id` bigint(20) NOT NULL,
  `rendement` double DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `execution_production`
--

INSERT INTO `execution_production` (`id_execution_production`, `controle_temperature`, `date_debut`, `date_fin_prevue`, `date_fin_reelle`, `observations`, `reference`, `statut`, `guide_production_id`, `lot_olives_id`, `rendement`) VALUES
(1, b'0', '2026-05-04', '2026-05-05', '2026-05-04', 'test', 'EXE-LO01-G1-M5-20260504202732195', 'TERMINEE', 1, 1, NULL),
(2, b'0', '2026-05-04', '2026-05-05', '2026-05-04', 'aa', 'EXE-LO02-G1-M5-20260504212646614', 'TERMINEE', 1, 2, NULL),
(3, b'0', '2026-05-04', '2026-05-05', '2026-05-04', 'aa', 'EXE-LO04-G1-M5-20260504214842535', 'TERMINEE', 1, 4, 0),
(4, b'0', '2026-05-04', '2026-05-05', '2026-05-04', 'aa', 'EXE-LO05-G1-M5-20260504220117386', 'TERMINEE', 1, 5, 0),
(5, b'0', '2026-05-06', '2026-05-07', NULL, 'aa', 'EXE-LO06-G1-M5-20260506043249670', 'EN_COURS', 1, 6, NULL),
(6, b'0', '2026-05-06', '2026-05-07', '2026-05-06', 'aa', 'EXE-LO07-G1-M5-20260506043928352', 'TERMINEE', 1, 7, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `fournisseur`
--

CREATE TABLE `fournisseur` (
  `id_fournisseur` bigint(20) NOT NULL,
  `cin` varchar(255) NOT NULL,
  `nom` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `fournisseur`
--

INSERT INTO `fournisseur` (`id_fournisseur`, `cin`, `nom`) VALUES
(1, '123456789', 'moez');

-- --------------------------------------------------------

--
-- Table structure for table `guide_production`
--

CREATE TABLE `guide_production` (
  `id_guide_production` bigint(20) NOT NULL,
  `date_creation` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_machine` varchar(255) NOT NULL,
  `huilerie_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `guide_production`
--

INSERT INTO `guide_production` (`id_guide_production`, `date_creation`, `description`, `nom`, `reference`, `type_machine`, `huilerie_id`) VALUES
(1, '2026-05-04', 'test', 'test guide 3 phases', 'GP01', '3_phase', 1);

-- --------------------------------------------------------

--
-- Table structure for table `huilerie`
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `huilerie`
--

INSERT INTO `huilerie` (`id_huilerie`, `active`, `capacite_production`, `certification`, `localisation`, `nom`, `type`, `entreprise_id`) VALUES
(1, b'1', 500, 'iso', 'manouba', 'ma3sra', 'artisanale', 1),
(2, b'1', 100, 'iso', 'mahdia', 'zitounia', 'artisanale', 1);

-- --------------------------------------------------------

--
-- Table structure for table `lot_olives`
--

CREATE TABLE `lot_olives` (
  `id_lot` bigint(20) NOT NULL,
  `acidite_olives_pourcent` double DEFAULT NULL,
  `bon_pesee_pdf_path` varchar(255) DEFAULT NULL,
  `date_reception` varchar(255) DEFAULT NULL,
  `date_recolte` varchar(255) DEFAULT NULL,
  `duree_stockage_avant_broyage` int(11) DEFAULT NULL,
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
  `fournisseur_id` bigint(20) DEFAULT NULL,
  `huilerie_id` bigint(20) DEFAULT NULL,
  `matiere_premiere_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `lot_olives`
--

INSERT INTO `lot_olives` (`id_lot`, `acidite_olives_pourcent`, `bon_pesee_pdf_path`, `date_reception`, `date_recolte`, `duree_stockage_avant_broyage`, `humidite_pourcent`, `lavage_effectue`, `maturite`, `methode_recolte`, `origine`, `pesee`, `quantite_initiale`, `quantite_restante`, `reference`, `region`, `taux_feuilles_pourcent`, `temps_depuis_recolte_heures`, `type_sol`, `variete`, `campagne_id`, `fournisseur_id`, `huilerie_id`, `matiere_premiere_id`) VALUES
(1, 2, 'generated/bons-pesee/bon-pesee-LO01.pdf', '2026-05-04', '2026-05-04', 12, 20, 'Oui', '2', 'manuelle', 'mahdia', 1200, 1200, 0, 'LO01', 'Centre', 2, 12, 'calcaire', 'Chemlali', 1, 1, 1, 1),
(2, 2, 'generated/bons-pesee/bon-pesee-LO02.pdf', '2026-05-04', '2026-05-04', 1, 20, 'Non', '2', 'manuelle', 'mahdia', 200, 200, 0, 'LO02', 'Centre', 2, 12, 'calcaire', 'Chemlali', 1, 1, 1, 1),
(3, 2, 'generated/bons-pesee/bon-pesee-LO03.pdf', '2026-05-04', '2026-05-04', 1, 20, 'Oui', '2', 'manuelle', 'mahdia', 1200, 1200, 1200, 'LO03', 'Centre', 2, 12, 'calcaire', 'Chetoui', 2, 1, 2, 2),
(4, 2, 'generated/bons-pesee/bon-pesee-LO04.pdf', '2026-05-04', '2026-05-04', 1, 20, 'Oui', '2', 'manuelle', 'mahdia', 200, 200, 0, 'LO04', 'Centre', 2, 12, 'calcaire', 'Chemlali', 1, 1, 1, 1),
(5, 2, 'generated/bons-pesee/bon-pesee-LO05.pdf', '2026-05-04', '2026-05-04', 1, 20, 'Oui', '2', 'manuelle', 'mahdia', 1200, 1200, 0, 'LO05', 'Centre', 2, 12, 'calcaire', 'Chemlali', 1, 1, 1, 1),
(6, 2, 'generated/bons-pesee/bon-pesee-LO06.pdf', '2026-05-06', '2026-05-06', 1, 20, 'Oui', '2', 'manuelle', 'mahdia', 2000, 2000, 0, 'LO06', 'Centre', 2, 12, 'calcaire', 'Chemlali', 1, 1, 1, 1),
(7, 2, 'generated/bons-pesee/bon-pesee-LO07.pdf', '2026-05-06', '2026-05-06', 1, 20, 'Oui', '2', 'manuelle', 'mahdia', 2000, 2000, 0, 'LO07', 'Centre', 2, 12, 'calcaire', 'Chemlali', 1, 1, 1, 1);

-- --------------------------------------------------------

--
-- Table structure for table `machine`
--

CREATE TABLE `machine` (
  `id_machine` bigint(20) NOT NULL,
  `capacite` int(11) DEFAULT NULL,
  `categorie_machine` varchar(255) DEFAULT NULL,
  `etat_machine` varchar(255) DEFAULT NULL,
  `nom_machine` varchar(255) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_machine` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `machine`
--

INSERT INTO `machine` (`id_machine`, `capacite`, `categorie_machine`, `etat_machine`, `nom_machine`, `reference`, `type_machine`, `huilerie_id`) VALUES
(1, 1200, 'broyage', 'EN_SERVICE', 'machine1', 'MC01', 'marteaux', 1),
(2, 200, 'malaxage', 'EN_SERVICE', 'machine2', 'MC02', 'vertical', 1),
(3, 200, 'extraction', 'EN_SERVICE', 'machine3', 'MC03', 'centrifugation_3_phases', 1),
(4, 200, 'separation', 'EN_SERVICE', 'machine4', 'MC04', 'decanteur_3_phases', 1),
(5, 200, 'nettoyage', 'EN_SERVICE', 'machine5', 'MC05', 'soufflerie', 1),
(6, 300, 'ajout_eau', 'EN_SERVICE', 'machine6', 'MC06', 'systeme_injection_eau', 1),
(7, 200, 'stockage', 'EN_SERVICE', 'machine7', 'MC07', 'cuve_fibre', 1),
(8, 200, 'broyage', 'EN_SERVICE', 'makina1', 'MC08', 'disques', 2),
(9, 200, 'malaxage', 'EN_SERVICE', 'makina2', 'MC09', 'vertical', 2);

-- --------------------------------------------------------

--
-- Table structure for table `matiere_premiere`
--

CREATE TABLE `matiere_premiere` (
  `id_matiere_premiere` bigint(20) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) DEFAULT NULL,
  `reference` varchar(255) NOT NULL,
  `type` varchar(255) DEFAULT NULL,
  `unite_mesure` varchar(255) DEFAULT NULL,
  `huilerie_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `matiere_premiere`
--

INSERT INTO `matiere_premiere` (`id_matiere_premiere`, `description`, `nom`, `reference`, `type`, `unite_mesure`, `huilerie_id`) VALUES
(1, 'olive verte', 'zitoun', 'MP01', 'olive', 'kg', 1),
(2, 'olive noir', 'zitoun', 'MP02', 'olive', 'kg', 2);

-- --------------------------------------------------------

--
-- Table structure for table `module`
--

CREATE TABLE `module` (
  `id_module` bigint(20) NOT NULL,
  `nom` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `module`
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
-- Table structure for table `parametre_etape`
--

CREATE TABLE `parametre_etape` (
  `id_parametre_etape` bigint(20) NOT NULL,
  `code_parametre` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `unite_mesure` varchar(255) DEFAULT NULL,
  `valeur_estime` varchar(255) DEFAULT NULL,
  `etape_production_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `parametre_etape`
--

INSERT INTO `parametre_etape` (`id_parametre_etape`, `code_parametre`, `description`, `nom`, `unite_mesure`, `valeur_estime`, `etape_production_id`) VALUES
(1, 'temperature_malaxage_c', 'Temperature de malaxage', 'Temperature de malaxage', 'C', '27', 4),
(2, 'duree_malaxage_min', 'Duree de malaxage', 'Duree de malaxage', 'min', '40', 4),
(3, 'presence_ajout_eau', '1 = ajout d\'eau actif', 'Presence ajout eau', 'bool', '1', 5),
(4, 'vitesse_decanteur_tr_min', 'Vitesse du decanteur 3 phases', 'Vitesse du decanteur', 'tr/min', '3200', 6),
(5, 'presence_separateur', '1 = separateur obligatoire', 'Presence separateur', 'bool', '1', 6);

-- --------------------------------------------------------

--
-- Table structure for table `password_reset_tokens`
--

CREATE TABLE `password_reset_tokens` (
  `id` bigint(20) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  `token` varchar(255) NOT NULL,
  `used` bit(1) NOT NULL,
  `utilisateur_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `permission`
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `permission`
--

INSERT INTO `permission` (`id_privilege`, `can_create`, `can_delete`, `can_executed`, `can_read`, `can_update`, `date_creation`, `description`, `module_id`, `profil_id`) VALUES
(1, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 1, 1),
(2, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 2, 1),
(3, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 3, 1),
(4, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 4, 1),
(5, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 5, 1),
(6, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 6, 1),
(7, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 7, 1),
(8, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 8, 1),
(9, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 9, 1),
(10, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 10, 1),
(11, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 11, 1),
(12, b'1', b'1', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 12, 1),
(13, b'0', b'0', b'0', b'1', b'0', '2026-05-04 18:59:16.000000', NULL, 1, 2),
(14, b'1', b'0', b'1', b'1', b'0', '2026-05-04 18:59:16.000000', NULL, 2, 2),
(15, b'1', b'0', b'0', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 3, 2),
(16, b'1', b'0', b'1', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 4, 2),
(17, b'0', b'0', b'0', b'1', b'0', '2026-05-04 18:59:16.000000', NULL, 5, 2),
(18, b'1', b'0', b'0', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 6, 2),
(19, b'1', b'0', b'0', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 7, 2),
(20, b'1', b'0', b'0', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 8, 2),
(21, b'1', b'0', b'0', b'1', b'1', '2026-05-04 18:59:16.000000', NULL, 9, 2),
(22, b'0', b'0', b'0', b'0', b'0', '2026-05-04 18:59:16.000000', NULL, 10, 2),
(23, b'0', b'0', b'0', b'0', b'0', '2026-05-04 18:59:16.000000', NULL, 11, 2),
(24, b'0', b'0', b'0', b'0', b'0', '2026-05-04 18:59:16.000000', NULL, 12, 2);

-- --------------------------------------------------------

--
-- Table structure for table `prediction`
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `prediction`
--

INSERT INTO `prediction` (`id_prediction`, `date_creation`, `mode_prediction`, `probabilite_qualite`, `qualite_predite`, `quantite_huile_recalculee_litres`, `rendement_predit_pourcent`, `execution_production_id`) VALUES
(1, '2026-05-04T20:27:38.2830855', 'with_lab', 0.8421, 'Lampante', 173.41, 15.71, 1),
(2, '2026-05-04T21:27:04.1458564', 'no_lab', 0.4561, 'Vierge', 32.08, 17.43, 2),
(3, '2026-05-04T21:48:44.8406796', 'no_lab', 0.4561, 'Vierge', 32.08, 17.43, 3),
(4, '2026-05-04T22:01:21.3548086', 'no_lab', 0.4561, 'Vierge', 192.47, 17.43, 4),
(5, '2026-05-06T04:39:35.0639208', 'no_lab', 0.4903, 'Vierge', 316.1, 17.18, 6);

-- --------------------------------------------------------

--
-- Table structure for table `produit_final`
--

CREATE TABLE `produit_final` (
  `id_produit` bigint(20) NOT NULL,
  `date_production` varchar(255) DEFAULT NULL,
  `nom_produit` varchar(255) DEFAULT NULL,
  `qualite` varchar(255) DEFAULT NULL,
  `quantite_produite` double DEFAULT NULL,
  `reference` varchar(255) NOT NULL,
  `execution_production_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `produit_final`
--

INSERT INTO `produit_final` (`id_produit`, `date_production`, `nom_produit`, `qualite`, `quantite_produite`, `reference`, `execution_production_id`) VALUES
(1, '2026-05-04', 'Huile Chemlali', 'lampante', 175, 'PF01', 1),
(2, '2026-05-04', 'Huile Chemlali', 'vierge', 32, 'PF02', 2),
(3, '2026-05-04', 'Huile Chemlali', 'vierge', 32, 'PF03', 3),
(4, '2026-05-04', 'Huile Chemlali', 'vierge', 190, 'PF04', 4),
(5, '2026-05-06', 'Huile Chemlali', 'vierge', 300, 'PF05', 6);

-- --------------------------------------------------------

--
-- Table structure for table `profil`
--

CREATE TABLE `profil` (
  `id_profil` bigint(20) NOT NULL,
  `date_creation` datetime(6) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `profil`
--

INSERT INTO `profil` (`id_profil`, `date_creation`, `description`, `nom`) VALUES
(1, '2026-05-04 18:59:15.000000', 'Acces total', 'ADMIN'),
(2, '2026-05-04 18:59:16.000000', 'Acces operations metier', 'RESPONSABLE_PRODUCTION');

-- --------------------------------------------------------

--
-- Table structure for table `refresh_tokens`
--

CREATE TABLE `refresh_tokens` (
  `id` bigint(20) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  `revoked` bit(1) NOT NULL,
  `token` varchar(255) NOT NULL,
  `utilisateur_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `refresh_tokens`
--

INSERT INTO `refresh_tokens` (`id`, `expires_at`, `revoked`, `token`, `utilisateur_id`) VALUES
(1, '2026-05-11 19:04:31.000000', b'0', '0f96e719-db80-4328-a2a1-9d874fbf61ee', 1),
(2, '2026-05-13 01:04:37.000000', b'0', '4fa6dbd4-38b6-4c1d-9dbe-81b97e697442', 1),
(3, '2026-05-13 02:46:13.000000', b'0', '97b1236f-79c3-4d09-b951-7bc8e7dad6cb', 1);

-- --------------------------------------------------------

--
-- Table structure for table `stock`
--

CREATE TABLE `stock` (
  `id_stock` bigint(20) NOT NULL,
  `quantite_disponible` double DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_stock` varchar(255) DEFAULT NULL,
  `variete` varchar(255) DEFAULT NULL,
  `lot_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `stock`
--

INSERT INTO `stock` (`id_stock`, `quantite_disponible`, `reference`, `type_stock`, `variete`, `lot_id`) VALUES
(1, 0, 'ST01', 'olive', 'chemlali', 7),
(2, 1200, 'ST02', 'olive', 'chetoui', 3);

-- --------------------------------------------------------

--
-- Table structure for table `stock_movement`
--

CREATE TABLE `stock_movement` (
  `id_stock_movement` bigint(20) NOT NULL,
  `commentaire` varchar(255) DEFAULT NULL,
  `date_mouvement` varchar(255) DEFAULT NULL,
  `reference` varchar(255) DEFAULT NULL,
  `type_mouvement` enum('AJUSTEMENT','ENTREE','TRANSFERT') DEFAULT NULL,
  `lot_id` bigint(20) DEFAULT NULL,
  `stock_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `stock_movement`
--

INSERT INTO `stock_movement` (`id_stock_movement`, `commentaire`, `date_mouvement`, `reference`, `type_mouvement`, `lot_id`, `stock_id`) VALUES
(1, 'Arrivage lot LO01', '2026-05-04', 'MS01', 'ENTREE', 1, 1),
(2, 'Arrivage lot LO02', '2026-05-04', 'MS02', 'ENTREE', 2, 1),
(3, 'Arrivage lot LO03', '2026-05-04', 'MS03', 'ENTREE', 3, 2),
(4, 'Transfert automatique lors de l\'execution EXE-LO01-G1-M5-20260504202732195', '2026-05-04', 'MS04', 'TRANSFERT', 1, 1),
(5, 'Transfert automatique lors de l\'execution EXE-LO02-G1-M5-20260504212646614', '2026-05-04', 'MS05', 'TRANSFERT', 2, 1),
(6, 'Arrivage lot LO04', '2026-05-04', 'MS06', 'ENTREE', 4, 1),
(7, 'Transfert automatique lors de l\'execution EXE-LO04-G1-M5-20260504214842535', '2026-05-04', 'MS07', 'TRANSFERT', 4, 1),
(8, 'Arrivage lot LO05', '2026-05-04', 'MS08', 'ENTREE', 5, 1),
(9, 'Transfert automatique lors de l\'execution EXE-LO05-G1-M5-20260504220117386', '2026-05-04', 'MS09', 'TRANSFERT', 5, 1),
(10, 'Arrivage lot LO06', '2026-05-06', 'MS10', 'ENTREE', 6, 1),
(11, 'Transfert automatique lors de l\'execution EXE-LO06-G1-M5-20260506043249670', '2026-05-06', 'MS11', 'TRANSFERT', 6, 1),
(12, 'Arrivage lot LO07', '2026-05-06', 'MS12', 'ENTREE', 7, 1),
(13, 'Transfert automatique lors de l\'execution EXE-LO07-G1-M5-20260506043928352', '2026-05-06', 'MS13', 'TRANSFERT', 7, 1);

-- --------------------------------------------------------

--
-- Table structure for table `utilisateur`
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `utilisateur`
--

INSERT INTO `utilisateur` (`id_utilisateur`, `actif`, `email`, `email_verified`, `mot_de_passe`, `nom`, `prenom`, `telephone`, `verification_token`, `verification_token_expires_at`, `profil_id`) VALUES
(1, 'ACTIF', 'admin@default.com', b'1', '$2a$10$fuxRjiA.tqKHhGCnsyfuu.yUS/rGgaPIWB761F4Ks54haJBOaLv1G', 'Admin', 'Système', NULL, '87c22d4d-b53e-4a76-afbc-ff53bc765753', '2026-05-05 19:02:25.000000', 1);

-- --------------------------------------------------------

--
-- Table structure for table `valeur_reelle_parametre`
--

CREATE TABLE `valeur_reelle_parametre` (
  `id_valeur_reelle_parametre` bigint(20) NOT NULL,
  `date_creation` datetime(6) DEFAULT NULL,
  `date_modification` datetime(6) DEFAULT NULL,
  `deviation` double DEFAULT NULL,
  `qualite_deviation` varchar(255) DEFAULT NULL,
  `valeur_reelle` double NOT NULL,
  `execution_production_id` bigint(20) NOT NULL,
  `parametre_etape_id` bigint(20) NOT NULL,
  `unite_mesure` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `valeur_reelle_parametre`
--

INSERT INTO `valeur_reelle_parametre` (`id_valeur_reelle_parametre`, `date_creation`, `date_modification`, `deviation`, `qualite_deviation`, `valeur_reelle`, `execution_production_id`, `parametre_etape_id`, `unite_mesure`) VALUES
(1, '2026-05-04 19:28:17.000000', '2026-05-04 19:28:17.000000', NULL, NULL, 27, 1, 1, NULL),
(2, '2026-05-04 19:28:17.000000', '2026-05-04 19:28:17.000000', NULL, NULL, 40, 1, 2, NULL),
(3, '2026-05-04 19:28:17.000000', '2026-05-04 19:28:17.000000', NULL, NULL, 1, 1, 3, NULL),
(4, '2026-05-04 19:28:17.000000', '2026-05-04 19:28:17.000000', NULL, NULL, 3100, 1, 4, NULL),
(5, '2026-05-04 19:28:17.000000', '2026-05-04 19:28:17.000000', NULL, NULL, 1, 1, 5, NULL),
(6, '2026-05-04 20:34:30.000000', '2026-05-04 20:34:30.000000', NULL, NULL, 27, 2, 1, NULL),
(7, '2026-05-04 20:34:30.000000', '2026-05-04 20:34:30.000000', NULL, NULL, 40, 2, 2, NULL),
(8, '2026-05-04 20:34:30.000000', '2026-05-04 20:34:30.000000', NULL, NULL, 1, 2, 3, NULL),
(9, '2026-05-04 20:34:30.000000', '2026-05-04 20:34:30.000000', NULL, NULL, 3000, 2, 4, NULL),
(10, '2026-05-04 20:34:30.000000', '2026-05-04 20:34:30.000000', NULL, NULL, 1, 2, 5, NULL),
(11, '2026-05-04 20:49:08.000000', '2026-05-04 20:49:08.000000', NULL, NULL, 27, 3, 1, NULL),
(12, '2026-05-04 20:49:08.000000', '2026-05-04 20:49:08.000000', NULL, NULL, 40, 3, 2, NULL),
(13, '2026-05-04 20:49:08.000000', '2026-05-04 20:49:08.000000', NULL, NULL, 1, 3, 3, NULL),
(14, '2026-05-04 20:49:08.000000', '2026-05-04 20:49:08.000000', NULL, NULL, 3100, 3, 4, NULL),
(15, '2026-05-04 20:49:08.000000', '2026-05-04 20:49:08.000000', NULL, NULL, 1, 3, 5, NULL),
(16, '2026-05-04 21:01:55.000000', '2026-05-04 21:01:55.000000', 0, 'FAIBLE', 27, 4, 1, NULL),
(17, '2026-05-04 21:01:55.000000', '2026-05-04 21:01:55.000000', 0, 'FAIBLE', 40, 4, 2, NULL),
(18, '2026-05-04 21:01:55.000000', '2026-05-04 21:01:55.000000', 0, 'FAIBLE', 1, 4, 3, NULL),
(19, '2026-05-04 21:01:55.000000', '2026-05-04 21:01:55.000000', -3.125, 'FAIBLE', 3100, 4, 4, NULL),
(20, '2026-05-04 21:01:55.000000', '2026-05-04 21:01:55.000000', 0, 'FAIBLE', 1, 4, 5, NULL),
(21, '2026-05-06 03:40:19.000000', '2026-05-06 03:40:19.000000', -44.44444444444444, 'IMPORTANTE', 15, 6, 1, NULL),
(22, '2026-05-06 03:40:19.000000', '2026-05-06 03:40:19.000000', -75, 'IMPORTANTE', 10, 6, 2, NULL),
(23, '2026-05-06 03:40:19.000000', '2026-05-06 03:40:19.000000', 0, 'FAIBLE', 1, 6, 3, NULL),
(24, '2026-05-06 03:40:19.000000', '2026-05-06 03:40:19.000000', -6.25, 'FAIBLE', 3000, 6, 4, NULL),
(25, '2026-05-06 03:40:19.000000', '2026-05-06 03:40:19.000000', 0, 'FAIBLE', 1, 6, 5, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `administrateur`
--
ALTER TABLE `administrateur`
  ADD PRIMARY KEY (`id_utilisateur`),
  ADD UNIQUE KEY `UK44tpalrodl9ytqk2c2n3deju1` (`entreprise_id_admin`);

--
-- Indexes for table `analyse_laboratoire`
--
ALTER TABLE `analyse_laboratoire`
  ADD PRIMARY KEY (`id_analyse`),
  ADD UNIQUE KEY `UKauftcdplhc9o41psn6750p1sx` (`lot_id`);

--
-- Indexes for table `campagne_olives`
--
ALTER TABLE `campagne_olives`
  ADD PRIMARY KEY (`id_campagne`),
  ADD UNIQUE KEY `UK9ty5pnudb88ddlxnkg67odakn` (`reference`),
  ADD KEY `FKs8t2iqfuwiums9vdl56spk7hy` (`huilerie_id`);

--
-- Indexes for table `employe`
--
ALTER TABLE `employe`
  ADD PRIMARY KEY (`id_utilisateur`),
  ADD KEY `FK24v5ii6k1yah62wr4t60axy3a` (`huilerie_id_emp`);

--
-- Indexes for table `entreprise`
--
ALTER TABLE `entreprise`
  ADD PRIMARY KEY (`id_entreprise`);

--
-- Indexes for table `etape_production`
--
ALTER TABLE `etape_production`
  ADD PRIMARY KEY (`id_etape_production`),
  ADD KEY `FKngcreaesaqqyx3hatkg732wao` (`guide_production_id`),
  ADD KEY `FKq4f7nnim5sxsqcf7a73bto8s8` (`machine_id`);

--
-- Indexes for table `execution_production`
--
ALTER TABLE `execution_production`
  ADD PRIMARY KEY (`id_execution_production`),
  ADD UNIQUE KEY `UKjvhjk2kg19xwqcw2y7mmjvyt2` (`reference`),
  ADD KEY `FKmeshbjvxaes4lyw7m9rawx1c8` (`guide_production_id`),
  ADD KEY `FK9fgw77gskwnvnob4fa4cub5x0` (`lot_olives_id`);

--
-- Indexes for table `fournisseur`
--
ALTER TABLE `fournisseur`
  ADD PRIMARY KEY (`id_fournisseur`),
  ADD UNIQUE KEY `UKp4le0e7xc0uqcxge0sawids7h` (`cin`);

--
-- Indexes for table `guide_production`
--
ALTER TABLE `guide_production`
  ADD PRIMARY KEY (`id_guide_production`),
  ADD UNIQUE KEY `UKdbuq3vdui95foprn92qp2ii1a` (`reference`),
  ADD KEY `FK19wxgw32srw4p5426w82wfemd` (`huilerie_id`);

--
-- Indexes for table `huilerie`
--
ALTER TABLE `huilerie`
  ADD PRIMARY KEY (`id_huilerie`),
  ADD UNIQUE KEY `uk_huilerie_nom` (`nom`),
  ADD KEY `FK6lxie70n87jisvfj9ga3j5fwf` (`entreprise_id`);

--
-- Indexes for table `lot_olives`
--
ALTER TABLE `lot_olives`
  ADD PRIMARY KEY (`id_lot`),
  ADD UNIQUE KEY `UKe12qqum22imabxjowbj5qylp0` (`reference`),
  ADD KEY `FKdc5p6f7rm7hut99vh64ct2dsn` (`fournisseur_id`);

--
-- Indexes for table `machine`
--
ALTER TABLE `machine`
  ADD PRIMARY KEY (`id_machine`),
  ADD UNIQUE KEY `UKrwc4ysfgi3rc8nws96lianqyt` (`reference`),
  ADD KEY `FK7awy44m6t3cr5bieg6mcn7rj6` (`huilerie_id`);

--
-- Indexes for table `matiere_premiere`
--
ALTER TABLE `matiere_premiere`
  ADD PRIMARY KEY (`id_matiere_premiere`),
  ADD UNIQUE KEY `UKi7g03id651f2rn7yicrvudnar` (`reference`);

--
-- Indexes for table `module`
--
ALTER TABLE `module`
  ADD PRIMARY KEY (`id_module`),
  ADD UNIQUE KEY `uk_module_nom` (`nom`);

--
-- Indexes for table `parametre_etape`
--
ALTER TABLE `parametre_etape`
  ADD PRIMARY KEY (`id_parametre_etape`),
  ADD KEY `FKn33lu4fe47o1yqh5rurykmyv5` (`etape_production_id`);

--
-- Indexes for table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `UK71lqwbwtklmljk3qlsugr1mig` (`token`),
  ADD KEY `idx_password_reset_tokens_utilisateur_id` (`utilisateur_id`);

--
-- Indexes for table `permission`
--
ALTER TABLE `permission`
  ADD PRIMARY KEY (`id_privilege`),
  ADD UNIQUE KEY `uk_permission_profil_module` (`profil_id`,`module_id`),
  ADD KEY `idx_permission_profil_id` (`profil_id`),
  ADD KEY `idx_permission_module_id` (`module_id`);

--
-- Indexes for table `prediction`
--
ALTER TABLE `prediction`
  ADD PRIMARY KEY (`id_prediction`),
  ADD KEY `FKj6tsqot6di22fojhgt55y7x0g` (`execution_production_id`);

--
-- Indexes for table `produit_final`
--
ALTER TABLE `produit_final`
  ADD PRIMARY KEY (`id_produit`),
  ADD UNIQUE KEY `UK7cdn25ccec1pdyh0c8ndvdewn` (`reference`),
  ADD KEY `FKq12xc6sk9sem5coy8jg2ygjjl` (`execution_production_id`);

--
-- Indexes for table `profil`
--
ALTER TABLE `profil`
  ADD PRIMARY KEY (`id_profil`),
  ADD UNIQUE KEY `uk_profil_nom` (`nom`);

--
-- Indexes for table `refresh_tokens`
--
ALTER TABLE `refresh_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `UKghpmfn23vmxfu3spu3lfg4r2d` (`token`),
  ADD KEY `idx_refresh_tokens_utilisateur_id` (`utilisateur_id`);

--
-- Indexes for table `stock`
--
ALTER TABLE `stock`
  ADD PRIMARY KEY (`id_stock`),
  ADD KEY `FKahn3gfs4jg4dh0cfjmmq66xtq` (`lot_id`);

--
-- Indexes for table `stock_movement`
--
ALTER TABLE `stock_movement`
  ADD PRIMARY KEY (`id_stock_movement`),
  ADD KEY `FKkd9a4774f6adw0i0q6xy4tgpv` (`lot_id`),
  ADD KEY `FKs3qeghgdh1ye5iecin4v9jsjk` (`stock_id`);

--
-- Indexes for table `utilisateur`
--
ALTER TABLE `utilisateur`
  ADD PRIMARY KEY (`id_utilisateur`),
  ADD UNIQUE KEY `UKrma38wvnqfaf66vvmi57c71lo` (`email`),
  ADD UNIQUE KEY `UKhtdd6m7831984elvqeip9u78a` (`verification_token`),
  ADD KEY `idx_utilisateur_id` (`id_utilisateur`),
  ADD KEY `FKssvnc79lcj8l1hwgm230fiuh7` (`profil_id`);

--
-- Indexes for table `valeur_reelle_parametre`
--
ALTER TABLE `valeur_reelle_parametre`
  ADD PRIMARY KEY (`id_valeur_reelle_parametre`),
  ADD KEY `FKaoim1v7qmeesyv3gjudk2d03` (`execution_production_id`),
  ADD KEY `FKix44cxx4m626tfiw4eqyjx89v` (`parametre_etape_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `analyse_laboratoire`
--
ALTER TABLE `analyse_laboratoire`
  MODIFY `id_analyse` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `campagne_olives`
--
ALTER TABLE `campagne_olives`
  MODIFY `id_campagne` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `entreprise`
--
ALTER TABLE `entreprise`
  MODIFY `id_entreprise` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `etape_production`
--
ALTER TABLE `etape_production`
  MODIFY `id_etape_production` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `execution_production`
--
ALTER TABLE `execution_production`
  MODIFY `id_execution_production` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `fournisseur`
--
ALTER TABLE `fournisseur`
  MODIFY `id_fournisseur` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `guide_production`
--
ALTER TABLE `guide_production`
  MODIFY `id_guide_production` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `huilerie`
--
ALTER TABLE `huilerie`
  MODIFY `id_huilerie` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `lot_olives`
--
ALTER TABLE `lot_olives`
  MODIFY `id_lot` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `machine`
--
ALTER TABLE `machine`
  MODIFY `id_machine` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `matiere_premiere`
--
ALTER TABLE `matiere_premiere`
  MODIFY `id_matiere_premiere` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `module`
--
ALTER TABLE `module`
  MODIFY `id_module` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT for table `parametre_etape`
--
ALTER TABLE `parametre_etape`
  MODIFY `id_parametre_etape` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `permission`
--
ALTER TABLE `permission`
  MODIFY `id_privilege` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT for table `prediction`
--
ALTER TABLE `prediction`
  MODIFY `id_prediction` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `produit_final`
--
ALTER TABLE `produit_final`
  MODIFY `id_produit` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `profil`
--
ALTER TABLE `profil`
  MODIFY `id_profil` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `refresh_tokens`
--
ALTER TABLE `refresh_tokens`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `stock`
--
ALTER TABLE `stock`
  MODIFY `id_stock` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `stock_movement`
--
ALTER TABLE `stock_movement`
  MODIFY `id_stock_movement` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT for table `utilisateur`
--
ALTER TABLE `utilisateur`
  MODIFY `id_utilisateur` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `valeur_reelle_parametre`
--
ALTER TABLE `valeur_reelle_parametre`
  MODIFY `id_valeur_reelle_parametre` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=26;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `administrateur`
--
ALTER TABLE `administrateur`
  ADD CONSTRAINT `FKdib6ntq8vwh62bdimb3w32xki` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id_utilisateur`),
  ADD CONSTRAINT `FKggsidf5g9yf7t7ifpqec5k7sv` FOREIGN KEY (`entreprise_id_admin`) REFERENCES `entreprise` (`id_entreprise`);

--
-- Constraints for table `analyse_laboratoire`
--
ALTER TABLE `analyse_laboratoire`
  ADD CONSTRAINT `FKgm49rmfni4udndy59c6ri40w7` FOREIGN KEY (`lot_id`) REFERENCES `lot_olives` (`id_lot`);

--
-- Constraints for table `campagne_olives`
--
ALTER TABLE `campagne_olives`
  ADD CONSTRAINT `FKs8t2iqfuwiums9vdl56spk7hy` FOREIGN KEY (`huilerie_id`) REFERENCES `huilerie` (`id_huilerie`);

--
-- Constraints for table `employe`
--
ALTER TABLE `employe`
  ADD CONSTRAINT `FK24v5ii6k1yah62wr4t60axy3a` FOREIGN KEY (`huilerie_id_emp`) REFERENCES `huilerie` (`id_huilerie`),
  ADD CONSTRAINT `FKejqi2vsm7p30774s5rkfnridf` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id_utilisateur`);

--
-- Constraints for table `etape_production`
--
ALTER TABLE `etape_production`
  ADD CONSTRAINT `FKngcreaesaqqyx3hatkg732wao` FOREIGN KEY (`guide_production_id`) REFERENCES `guide_production` (`id_guide_production`),
  ADD CONSTRAINT `FKq4f7nnim5sxsqcf7a73bto8s8` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`id_machine`);

--
-- Constraints for table `execution_production`
--
ALTER TABLE `execution_production`
  ADD CONSTRAINT `FK9fgw77gskwnvnob4fa4cub5x0` FOREIGN KEY (`lot_olives_id`) REFERENCES `lot_olives` (`id_lot`),
  ADD CONSTRAINT `FKmeshbjvxaes4lyw7m9rawx1c8` FOREIGN KEY (`guide_production_id`) REFERENCES `guide_production` (`id_guide_production`);

--
-- Constraints for table `guide_production`
--
ALTER TABLE `guide_production`
  ADD CONSTRAINT `FK19wxgw32srw4p5426w82wfemd` FOREIGN KEY (`huilerie_id`) REFERENCES `huilerie` (`id_huilerie`);

--
-- Constraints for table `huilerie`
--
ALTER TABLE `huilerie`
  ADD CONSTRAINT `FK6lxie70n87jisvfj9ga3j5fwf` FOREIGN KEY (`entreprise_id`) REFERENCES `entreprise` (`id_entreprise`);

--
-- Constraints for table `lot_olives`
--
ALTER TABLE `lot_olives`
  ADD CONSTRAINT `FKdc5p6f7rm7hut99vh64ct2dsn` FOREIGN KEY (`fournisseur_id`) REFERENCES `fournisseur` (`id_fournisseur`);

--
-- Constraints for table `machine`
--
ALTER TABLE `machine`
  ADD CONSTRAINT `FK7awy44m6t3cr5bieg6mcn7rj6` FOREIGN KEY (`huilerie_id`) REFERENCES `huilerie` (`id_huilerie`);

--
-- Constraints for table `parametre_etape`
--
ALTER TABLE `parametre_etape`
  ADD CONSTRAINT `FKn33lu4fe47o1yqh5rurykmyv5` FOREIGN KEY (`etape_production_id`) REFERENCES `etape_production` (`id_etape_production`);

--
-- Constraints for table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD CONSTRAINT `FKeibiibmif85i859utr8rl5vf` FOREIGN KEY (`utilisateur_id`) REFERENCES `utilisateur` (`id_utilisateur`);

--
-- Constraints for table `permission`
--
ALTER TABLE `permission`
  ADD CONSTRAINT `FKrblidv8pvif32dp9fe2f0i9pp` FOREIGN KEY (`profil_id`) REFERENCES `profil` (`id_profil`),
  ADD CONSTRAINT `FKtnix0mh61fpm4o7cb7n3a5uj7` FOREIGN KEY (`module_id`) REFERENCES `module` (`id_module`);

--
-- Constraints for table `prediction`
--
ALTER TABLE `prediction`
  ADD CONSTRAINT `FKj6tsqot6di22fojhgt55y7x0g` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`);

--
-- Constraints for table `produit_final`
--
ALTER TABLE `produit_final`
  ADD CONSTRAINT `FKq12xc6sk9sem5coy8jg2ygjjl` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`);

--
-- Constraints for table `refresh_tokens`
--
ALTER TABLE `refresh_tokens`
  ADD CONSTRAINT `FKq2qrsiqa8xfqkhsxr5tuqt9ai` FOREIGN KEY (`utilisateur_id`) REFERENCES `utilisateur` (`id_utilisateur`);

--
-- Constraints for table `stock`
--
ALTER TABLE `stock`
  ADD CONSTRAINT `FKahn3gfs4jg4dh0cfjmmq66xtq` FOREIGN KEY (`lot_id`) REFERENCES `lot_olives` (`id_lot`);

--
-- Constraints for table `stock_movement`
--
ALTER TABLE `stock_movement`
  ADD CONSTRAINT `FKkd9a4774f6adw0i0q6xy4tgpv` FOREIGN KEY (`lot_id`) REFERENCES `lot_olives` (`id_lot`),
  ADD CONSTRAINT `FKs3qeghgdh1ye5iecin4v9jsjk` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`id_stock`);

--
-- Constraints for table `utilisateur`
--
ALTER TABLE `utilisateur`
  ADD CONSTRAINT `FKssvnc79lcj8l1hwgm230fiuh7` FOREIGN KEY (`profil_id`) REFERENCES `profil` (`id_profil`);

--
-- Constraints for table `valeur_reelle_parametre`
--
ALTER TABLE `valeur_reelle_parametre`
  ADD CONSTRAINT `FKaoim1v7qmeesyv3gjudk2d03` FOREIGN KEY (`execution_production_id`) REFERENCES `execution_production` (`id_execution_production`),
  ADD CONSTRAINT `FKix44cxx4m626tfiw4eqyjx89v` FOREIGN KEY (`parametre_etape_id`) REFERENCES `parametre_etape` (`id_parametre_etape`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
