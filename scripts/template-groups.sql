BEGIN TRANSACTION;

INSERT INTO auth_group VALUES(1, 'Editor');
INSERT INTO auth_group_permissions (group_id, permission_id)
SELECT 1, id FROM auth_permission WHERE codename IN
('change_wikipage', 'change_docstring', 'change_reviewcomment');

INSERT INTO auth_group VALUES(2, 'Reviewer');
INSERT INTO auth_group_permissions (group_id, permission_id)
SELECT 2, id FROM auth_permission WHERE codename IN
('change_wikipage', 'change_docstring', 'change_reviewcomment',
 'can_review');

COMMIT;
