create database if not exists code_analyzer
character set utf8mb4       -- utf8mb4 türkçe karakter destekler 
collate utf8mb4_unicode_ci; -- collate: metin karşılaştırma kuralları ci: case insensitive büyük küçük harf duyarsız 
use code_analyzer;
create table if not exists users(
   id int auto_increment primary key,
   username varchar(50) not null unique,
   password varchar(50) not null,
   role enum('student','teacher') not null, -- sadece iki durumdan biri olması için enum
   created_at timestamp default current_timestamp
);
   
