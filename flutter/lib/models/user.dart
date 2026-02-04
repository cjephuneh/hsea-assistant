class User {
  final int id;
  final String email;
  final String name;
  final String? phone;

  User({
    required this.id,
    required this.email,
    required this.name,
    this.phone,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      name: json['name'],
      phone: json['phone'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'name': name,
      'phone': phone,
    };
  }
}
