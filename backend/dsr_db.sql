-- ==========================================================
-- Script de Criação e População do Banco de Dados: dsr_db
-- Compatível com MySQL Workbench / MySQL Server 8+ / MariaDB
-- ==========================================================

-- 1. Criação do Banco de Dados
CREATE DATABASE IF NOT EXISTS `dsr_db`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `dsr_db`;

-- 2. Desativa checagem de chaves temporariamente para recriação limpa
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `imagem`;
DROP TABLE IF EXISTS `algoritmo`;
DROP TABLE IF EXISTS `usuario`;
SET FOREIGN_KEY_CHECKS = 1;

-- 3. Tabela: usuario
CREATE TABLE `usuario` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nome` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `senha_hash` VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Tabela: algoritmo
CREATE TABLE `algoritmo` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `tipo` VARCHAR(100) NOT NULL,
  `parametros` TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Tabela: imagem
CREATE TABLE `imagem` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL,
  `algoritmo_id` INT NULL,
  `nomeArquivo` VARCHAR(255) NOT NULL,
  `formato` VARCHAR(50) NOT NULL,
  `resolucao` VARCHAR(50) NOT NULL,
  `tamanho` DOUBLE NOT NULL COMMENT 'Tamanho do arquivo em KB/MB',
  `dadosOriginal` LONGBLOB NOT NULL COMMENT 'Blob da imagem original',
  `dadosProcessada` LONGBLOB NULL COMMENT 'Blob da imagem processada',
  CONSTRAINT `fk_imagem_usuario`
    FOREIGN KEY (`usuario_id`)
    REFERENCES `usuario` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_imagem_algoritmo`
    FOREIGN KEY (`algoritmo_id`)
    REFERENCES `algoritmo` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Inserção do Usuário Default: admin (senha: 'admin')
INSERT INTO `usuario` (`id`, `nome`, `email`, `senha_hash`)
VALUES (
  1,
  'admin',
  'admin@dsr.com',
  'pbkdf2_sha256$1000000$jIySXp85f1t5jJfh69sxb8$HAYqI3VLwGZoveyUnQYl3d1nJVi5gBBSJZk8NZPCmW0='
) ON DUPLICATE KEY UPDATE `nome` = VALUES(`nome`);
