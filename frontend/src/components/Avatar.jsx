export default function Avatar({ person }) {
  return (
    <div className="avatar" style={{ '--avatar-color': person.color }} aria-label={person.name}>
      <span>{person.initials}</span>
    </div>
  );
}
