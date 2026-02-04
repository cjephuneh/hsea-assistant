import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../services/task_service.dart';
import '../../services/notification_service.dart';
import '../tasks/task_list_screen.dart';
import '../voice/voice_assistant_screen.dart';
import '../meetings/meetings_screen.dart';
import '../reports/reports_screen.dart';
import '../profile/profile_screen.dart';
import '../workspaces/workspace_selector_screen.dart';
import '../templates/templates_screen.dart';
import '../tasks/create_task_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const TaskListScreen(),
    const VoiceAssistantScreen(),
    const MeetingsScreen(),
    const ReportsScreen(),
    const ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() => _currentIndex = index);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment),
            label: 'Tasks',
          ),
          NavigationDestination(
            icon: Icon(Icons.mic_outlined),
            selectedIcon: Icon(Icons.mic),
            label: 'Voice',
          ),
          NavigationDestination(
            icon: Icon(Icons.video_call_outlined),
            selectedIcon: Icon(Icons.video_call),
            label: 'Meetings',
          ),
          NavigationDestination(
            icon: Icon(Icons.analytics_outlined),
            selectedIcon: Icon(Icons.analytics),
            label: 'Reports',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
      floatingActionButton: _currentIndex == 0
          ? FloatingActionButton.extended(
              onPressed: () async {
                final result = await showModalBottomSheet(
                  context: context,
                  builder: (context) => Container(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ListTile(
                          leading: const Icon(Icons.add_task),
                          title: const Text('Create Task'),
                          onTap: () {
                            Navigator.pop(context, 'create_task');
                          },
                        ),
                        ListTile(
                          leading: const Icon(Icons.description),
                          title: const Text('Use Template'),
                          onTap: () {
                            Navigator.pop(context, 'template');
                          },
                        ),
                        ListTile(
                          leading: const Icon(Icons.workspaces),
                          title: const Text('Switch Workspace'),
                          onTap: () {
                            Navigator.pop(context, 'workspace');
                          },
                        ),
                      ],
                    ),
                  ),
                );

                if (result == 'create_task') {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const CreateTaskScreen(),
                    ),
                  );
                } else if (result == 'template') {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const TemplatesScreen(),
                    ),
                  );
                } else if (result == 'workspace') {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const WorkspaceSelectorScreen(),
                    ),
                  );
                }
              },
              icon: const Icon(Icons.add),
              label: const Text('Quick Actions'),
            )
          : null,
    );
  }
}
