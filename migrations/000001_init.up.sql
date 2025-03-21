create table users (
  id bigint primary key,
  name varchar(20) unique not null,
  email text unique not null,
  timezone text not null
);

create table user_filter_settings (
  id serial primary key,
  user_id bigint references users (id),
  authors text,
  topics text,
  types text,
  sources text,
  links text[]
);