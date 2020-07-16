create schema if not exists themeal4_highlow collate utf8mb4_unicode_ci;

create table if not exists admins
(
	id int auto_increment
		primary key,
	username varchar(20) null,
	password varchar(200) null,
	permission_level int default 0 null,
	constraint admins_username_uindex
		unique (username)
);

create table if not exists analytics
(
	id int auto_increment
		primary key,
	num_users int null,
	num_oauth_users int null,
	num_friendships int null,
	num_highlows int null,
	date datetime default CURRENT_TIMESTAMP null
);

create table if not exists blacklisted_tokens
(
	id int auto_increment
		primary key,
	token text not null
)
collate=utf8_unicode_ci;

create table if not exists bug_reports
(
	id int auto_increment
		primary key,
	uid varchar(50) not null,
	message varchar(6000) not null,
	_timestamp timestamp default CURRENT_TIMESTAMP not null,
	title varchar(200) default '' null
);

create table if not exists comments
(
	id int auto_increment
		primary key,
	commentid mediumtext not null,
	highlowid mediumtext not null,
	uid mediumtext not null,
	message mediumtext not null,
	_timestamp timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP
)
collate=utf8mb4_bin;

create table if not exists devices
(
	id int auto_increment
		primary key,
	device_id text not null,
	uid text not null,
	platform int not null
)
collate=utf8_unicode_ci;

create table if not exists events
(
	id int auto_increment
		primary key,
	type text not null,
	data text null,
	_timestamp timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP
)
collate=utf8_unicode_ci;

create table if not exists flags
(
	id int auto_increment
		primary key,
	flagger text not null,
	highlowid text null,
	uid text null,
	_type text not null,
	open tinyint(1) default 1 null
)
collate=utf8_unicode_ci;

create table if not exists friends
(
	id int auto_increment
		primary key,
	initiator text not null,
	acceptor text not null,
	status int null
)
collate=utf8_unicode_ci;

create table if not exists highlows
(
	id int auto_increment
		primary key,
	highlowid text not null,
	uid text not null,
	high mediumtext charset utf8mb4 null,
	low mediumtext charset utf8mb4 null,
	high_image text null,
	low_image text null,
	total_likes int null,
	_timestamp timestamp default CURRENT_TIMESTAMP not null,
	_date varchar(11) default '' null,
	private tinyint(1) default 0 null
);

create table if not exists interests
(
	id int auto_increment primary key,
	name varchar(100) not null,
	interest_id mediumtext not null,
	constraint interests_id_uindex
		unique (id),
	constraint interests_name_uindex
		unique (name)
);

create table if not exists likes
(
	id int auto_increment
		primary key,
	highlowid text not null,
	uid text not null
)
collate=utf8_unicode_ci;

create table if not exists oauth_accounts
(
	provider_key varchar(2000) not null,
	uid varchar(128) not null,
	provider_name enum('apple', 'google') not null
);

create table if not exists onetime_requests
(
	request_id varchar(256) not null,
	response varchar(16000) default '{ "status": "success" }' null
);

create table if not exists requests
(
	id int auto_increment
		primary key,
	num_requests int not null
);

create table if not exists subscriptions
(
	id int auto_increment
		primary key,
	originalTransactionId varchar(1024) not null,
	latestExpiryDate datetime null,
	latestReceiptData varchar(15000) null,
	hasReceivedFreeTrial tinyint(1) null,
	isHavingBillingIssue tinyint(1) default 0 null
);

create table if not exists test
(
	id int auto_increment
		primary key,
	value1 int null,
	value2 int null
);

create table if not exists user_interests
(
	id int auto_increment primary key,
	uid mediumtext not null,
	interest mediumtext not null,
	constraint user_interests_id_uindex
		unique (id)
);


create table if not exists users
(
	id int auto_increment
		primary key,
	uid mediumtext not null,
	firstname mediumtext not null,
	lastname mediumtext not null,
	email mediumtext not null,
	password mediumtext not null,
	profileimage mediumtext not null,
	streak int default 0 null,
	bio varchar(2048) default '' null,
	times_flagged int default 0 null,
	banned tinyint(1) default 0 null,
	notify_new_friend_req tinyint(1) default 1 null,
	notify_new_friend_acc tinyint(1) default 1 null,
	notify_new_feed_item tinyint(1) default 1 null,
	notify_new_like tinyint(1) default 1 null,
	notify_new_comment tinyint(1) default 1 null,
	date_joined timestamp default CURRENT_TIMESTAMP null,
	platform int default 0 null
)
collate=utf8mb4_bin;


create table if not exists activities
(
    id int auto_increment not null primary key,
	activity_id mediumtext not null,
	uid mediumtext not null,
	type int not null,
	timestamp timestamp default CURRENT_TIMESTAMP,
	data longtext
) collate=utf8mb4_bin;

create table if not exists sharing
(
	id int auto_increment not null primary key,
	activity_id mediumtext not null,
	shared_with mediumtext not null
);