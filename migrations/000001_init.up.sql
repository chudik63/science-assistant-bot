create table users (
  id serial primary key,
  username varchar(20) unique not null,
  email text unique not null,
  password_hash text not null,
  phone_number text
);

create table user_filter_settings (
  id serial primary key,
  user_id bigint references users (id),
  keywords text[0],
  preferred_authors text[0],
  topics text[0],
  time_interval text[0],
  data_sources text[0]
);