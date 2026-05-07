export const players = [
  { id: 1, name: "Yao Konaté", pos: "PG", pts: 22, reb: 4, ast: 7, pm: "+14", age: 23, trend: [18,20,19,22,24,22] },
  { id: 2, name: "Aboubacar Diabaté", pos: "C", pts: 14, reb: 11, ast: 2, pm: "+8", age: 26, trend: [12,13,14,11,15,14] },
  { id: 3, name: "Mamadou Traoré", pos: "SF", pts: 18, reb: 6, ast: 3, pm: "+5", age: 24, trend: [16,17,15,18,19,18] },
  { id: 4, name: "Ibrahim Coulibaly", pos: "SG", pts: 11, reb: 3, ast: 5, pm: "-2", age: 21, trend: [9,10,11,10,12,11] },
  { id: 5, name: "Sekou Bamba", pos: "PF", pts: 9, reb: 8, ast: 1, pm: "+3", age: 28, trend: [8,9,7,9,10,9] },
];

export const academyPlayers = [
  { id: 1, name: "Fatim Coulibaly", age: "U18", pos: "PG", trend: "+18%", note: "Efficacité en hausse ce mois", stat: "19.4 pts/j", emerging: true },
  { id: 2, name: "Lamine Diallo", age: "U20", pos: "C", trend: "+12%", note: "Dominant en zone paint", stat: "12.1 reb/j", emerging: true },
  { id: 3, name: "Aminata Sanogo", age: "U16", pos: "SF", trend: "+9%", note: "Progression constante", stat: "14.7 pts/j", emerging: true },
  { id: 4, name: "Cheikh Ndiaye", age: "U18", pos: "SG", trend: "+4%", note: "Bon shooter 3pts", stat: "38% 3pts", emerging: false },
  { id: 5, name: "Oumar Sylla", age: "U20", pos: "PF", trend: "-2%", note: "En reprise après blessure", stat: "9.2 pts/j", emerging: false },
  { id: 6, name: "Koffi Asante", age: "U16", pos: "PG", trend: "+22%", note: "Talent exceptionnel U16", stat: "16.8 pts/j", emerging: true },
];

export const progressionData = [
  { month: "Sep", offRating: 98, defRating: 102, pace: 88 },
  { month: "Oct", offRating: 101, defRating: 99, pace: 90 },
  { month: "Nov", offRating: 104, defRating: 97, pace: 91 },
  { month: "Dec", offRating: 106, defRating: 95, pace: 92 },
  { month: "Jan", offRating: 105, defRating: 96, pace: 91 },
  { month: "Fev", offRating: 108, defRating: 93, pace: 93 },
  { month: "Mar", offRating: 111, defRating: 91, pace: 94 },
];

export const events = [
  { time: "02:14", type: "Dunk", player: "Aboubacar Diabaté", team: "ABC", icon: "dunk" },
  { time: "05:33", type: "Interception", player: "Yao Konaté", team: "ABC", icon: "steal" },
  { time: "08:47", type: "3 points", player: "Mamadou Traoré", team: "ABC", icon: "three" },
  { time: "11:22", type: "Faute provoquée", player: "Ibrahim Coulibaly", team: "ABC", icon: "foul" },
  { time: "14:05", type: "Contre", player: "Aboubacar Diabaté", team: "ABC", icon: "block" },
  { time: "16:39", type: "3 points", player: "Yao Konaté", team: "ABC", icon: "three" },
];

export const shotZones = [
  { zone: "paint", made: 18, attempted: 28, x: 250, y: 280 },
  { zone: "mid_left", made: 4, attempted: 10, x: 130, y: 220 },
  { zone: "mid_right", made: 5, attempted: 11, x: 370, y: 220 },
  { zone: "corner_left", made: 3, attempted: 7, x: 60, y: 160 },
  { zone: "corner_right", made: 4, attempted: 8, x: 440, y: 160 },
  { zone: "top_key", made: 6, attempted: 15, x: 250, y: 160 },
  { zone: "arc_left", made: 3, attempted: 9, x: 100, y: 280 },
  { zone: "arc_right", made: 4, attempted: 10, x: 400, y: 280 },
];
