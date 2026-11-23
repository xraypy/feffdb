VERSIONS = [(1, 'beta1', '2026-August-30', 'pre-release'),
            (2, '0.9.0', '2026-November-22', 'pre-release: add cluster table'),
            ]

feffdb_schema = """

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA page_size=8192;

create table version (id integer primary key,
                      tag text not null unique,
                      date text not null unique,
                      notes text);

create table info (key text primary key not null, value text not null);

create table element (z integer primary key not null, symbol text not null,
                      name text not null, mass float not null);

create table cif (id integer primary key autoincrement,
                  text blob not null,
                  space_group text not null,
                  formula text,
                  compound text,
                  source_db text,
                  source_id text);

create table cluster (id integer primary key autoincrement,
                      text blob not null,
                      type text not null,
                      formula  text,
                      compound text,
                      source   text,
                      notes    text);

create table feffinp (id integer primary key autoincrement,
                      text blob not null,
                      absorber integer not null,
                      edge text not null,
                      scatterers text not null,
                      natoms integer not null,
                      cif_id integer,
                      cluster_id integer default 0,
                      foreign key(absorber) references element(z),
                      foreign key(cif_id) references cif(id),
                      foreign key(cluster_id) references cluster(id));


create table feffdat (id integer primary key autoincrement,
                      absorber integer not null,
                      scatterer integer not null,
                      nleg integer not null,
                      reff float not null,
                      edge text not null,
                      degen integer not null,
                      geometry text not null,
                      label text not null unique,
                      description text,
                      feffinp_id integer,
                      text blob not null,
                      donator_id integer default 1,
                      foreign key(feffinp_id) references feffinp(id),
                      foreign key(absorber) references element(z),
                      foreign key(scatterer) references element(z),
                      foreign key(donator_id) references person(id) );

create table person (id integer primary key autoincrement,
                     email text not null unique,
                     name text, password text);

insert into person (email, name) values ('feffdb@local', 'feffdb library');

create table rating_enum (scoreval integer primary key not null, notes text);

insert into rating_enum (scoreval) values (1);
insert into rating_enum (scoreval) values (2);
insert into rating_enum (scoreval) values (3);
insert into rating_enum (scoreval) values (4);
insert into rating_enum (scoreval) values (5);

create table feffdat_rating (id integer primary key autoincrement,
                             score integer not null,
                             review text,
                             feffdat_id integer not null,
                             person_id integer not null,
                             foreign key(score) references rating_enum(scoreval),
                             foreign key(feffdat_id) references feffdat(id),
                             foreign key(person_id) references person(id) );

"""
