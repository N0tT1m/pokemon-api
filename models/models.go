package models

type Pokemon struct {
	Name           string   `json:"name"`
	URL            *string  `json:"url"`
	NationalNo     *string  `json:"national_no"`
	Types          []string `json:"types"`
	Species        *string  `json:"species"`
	Height         *string  `json:"height"`
	Weight         *string  `json:"weight"`
	Abilities      []string `json:"abilities"`
	EVYield        *string  `json:"ev_yield"`
	CatchRate      *string  `json:"catch_rate"`
	BaseFriendship *string  `json:"base_friendship"`
	BaseExp        *string  `json:"base_exp"`
	GrowthRate     *string  `json:"growth_rate"`
	EggGroups      []string `json:"egg_groups"`
	GenderRatio    *string  `json:"gender_ratio"`
	EggCycles      *string  `json:"egg_cycles"`
	HP             *int     `json:"hp"`
	Attack         *int     `json:"attack"`
	Defense        *int     `json:"defense"`
	SpAtk          *int     `json:"sp_atk"`
	SpDef          *int     `json:"sp_def"`
	Speed          *int     `json:"speed"`
	Total          *int     `json:"total"`
}

type TypeDefense struct {
	TypeName   string  `json:"type_name"`
	Multiplier float32 `json:"multiplier"`
}

type Evolution struct {
	Number      *string  `json:"number"`
	Name        string   `json:"name"`
	URL         *string  `json:"url"`
	Types       []string `json:"types"`
	EvolvesVia  *string  `json:"evolves_via"`
	EvolvesFrom *string  `json:"evolves_from"`
	ChainOrder  int      `json:"chain_order"`
}

type Move struct {
	LearnMethod string `json:"learn_method"`
	LevelOrTM   string `json:"level_or_tm"`
	Name        string `json:"name"`
	Type        string `json:"type"`
	Category    string `json:"category"`
	Power       *int   `json:"power"`
	Accuracy    *int   `json:"accuracy"`
}

type Location struct {
	Games     []string `json:"games"`
	Locations []string `json:"locations"`
}

type RegionalDexEntry struct {
	DexNumber   int      `json:"dex_number"`
	PokemonName string   `json:"pokemon_name"`
	Types       []string `json:"types"`
}

type NationalDexEntry struct {
	NationalNo  int    `json:"national_no"`
	PokemonName string `json:"pokemon_name"`
}

type PokemonListEntry struct {
	Name       string   `json:"name"`
	NationalNo *string  `json:"national_no"`
	Types      []string `json:"types"`
}

type ItemDetail struct {
	Name      string  `json:"name"`
	Category  *string `json:"category"`
	Effect    *string `json:"effect"`
	SpriteURL *string `json:"sprite_url"`
	BuyPrice  *int    `json:"buy_price"`
	SellPrice *int    `json:"sell_price"`
}

type MoveDetail struct {
	Name                  string   `json:"name"`
	Type                  *string  `json:"type"`
	Category              *string  `json:"category"`
	Power                 *int     `json:"power"`
	Accuracy              *int     `json:"accuracy"`
	PP                    *int     `json:"pp"`
	Effect                *string  `json:"effect"`
	EffectChance          *int     `json:"effect_chance"`
	Priority              *int     `json:"priority"`
	Target                *string  `json:"target"`
	GenerationIntroduced  *int     `json:"generation_introduced"`
	ZMoveEquivalent       *string  `json:"z_move_equivalent"`
	MaxMoveEquivalent     *string  `json:"max_move_equivalent"`
	ContestType           *string  `json:"contest_type"`
	Flags                 []string `json:"flags"`
}

type PokemonForm struct {
	PokemonName string   `json:"pokemon_name"`
	FormName    string   `json:"form_name"`
	Types       []string `json:"types"`
	Abilities   []string `json:"abilities"`
	Height      *string  `json:"height"`
	Weight      *string  `json:"weight"`
	HP          *int     `json:"hp"`
	Attack      *int     `json:"attack"`
	Defense     *int     `json:"defense"`
	SpAtk       *int     `json:"sp_atk"`
	SpDef       *int     `json:"sp_def"`
	Speed       *int     `json:"speed"`
	Total       *int     `json:"total"`
}

type EggMoveParent struct {
	PokemonName string `json:"pokemon_name"`
	MoveName    string `json:"move_name"`
	ParentName  string `json:"parent_name"`
}

type AbilityDetail struct {
	Name        string  `json:"name"`
	Description *string `json:"description"`
	Generation  *int    `json:"generation"`
}

type AbilityPokemon struct {
	PokemonName string `json:"pokemon_name"`
	IsHidden    bool   `json:"is_hidden"`
}

type PokedexEntry struct {
	GameVersion string `json:"game_version"`
	FlavorText  string `json:"flavor_text"`
}

type Nature struct {
	Name          string  `json:"name"`
	IncreasedStat *string `json:"increased_stat"`
	DecreasedStat *string `json:"decreased_stat"`
}

type LocationEncounter struct {
	Region          string   `json:"region"`
	RouteName       string   `json:"route_name"`
	PokemonName     string   `json:"pokemon_name"`
	Games           []string `json:"games"`
	EncounterMethod *string  `json:"encounter_method"`
	Rarity          *string  `json:"rarity"`
	LevelRange      *string  `json:"level_range"`
	TimeOfDay       *string  `json:"time_of_day"`
}

type Berry struct {
	Name             string  `json:"name"`
	NaturalGiftType  *string `json:"natural_gift_type"`
	NaturalGiftPower *int    `json:"natural_gift_power"`
	SizeMM           *int    `json:"size_mm"`
	Firmness         *string `json:"firmness"`
	Effect           *string `json:"effect"`
	GrowthTime       *int    `json:"growth_time"`
}

type BerryFlavor struct {
	Flavor  string `json:"flavor"`
	Potency int    `json:"potency"`
}

type ItemLocation struct {
	ItemName string  `json:"item_name"`
	Game     string  `json:"game"`
	Location string  `json:"location"`
	Method   *string `json:"method"`
}

type TmLocation struct {
	TmNumber string `json:"tm_number"`
	MoveName string `json:"move_name"`
	Game     string `json:"game"`
	Location string `json:"location"`
}

type WildHeldItem struct {
	PokemonName string `json:"pokemon_name"`
	Game        string `json:"game"`
	ItemName    string `json:"item_name"`
	Rarity      string `json:"rarity"`
}

type PokemonBiology struct {
	PokemonName string `json:"pokemon_name"`
	Biology     string `json:"biology"`
}

type PokemonName struct {
	Language      string `json:"language"`
	LocalizedName string `json:"localized_name"`
}

type PokemonSprite struct {
	SpriteType string `json:"sprite_type"`
	Generation string `json:"generation"`
	URL        string `json:"url"`
}

type PokemonGameLocation struct {
	PokemonName string  `json:"pokemon_name"`
	Game        string  `json:"game"`
	Location    string  `json:"location"`
	Method      *string `json:"method"`
}

type RaidEvent struct {
	ID          int     `json:"id"`
	PokemonName string  `json:"pokemon_name"`
	TeraType    *string `json:"tera_type"`
	StarRating  *int    `json:"star_rating"`
	EventStart  *string `json:"event_start"`
	EventEnd    *string `json:"event_end"`
	IsActive    bool    `json:"is_active"`
	SourceURL   *string `json:"source_url"`
	ScrapedAt   string  `json:"scraped_at"`
}

type RaidCounter struct {
	PokemonName    string  `json:"pokemon_name"`
	TeraType       *string `json:"tera_type"`
	CounterPokemon string  `json:"counter_pokemon"`
	Rank           *int    `json:"rank"`
	Notes          *string `json:"notes"`
}

type PokemonClassification struct {
	PokemonName          string  `json:"pokemon_name"`
	GenerationIntroduced *int    `json:"generation_introduced"`
	IsLegendary          bool    `json:"is_legendary"`
	IsMythical           bool    `json:"is_mythical"`
	IsUltraBeast         bool    `json:"is_ultra_beast"`
	IsBaby               bool    `json:"is_baby"`
	IsParadox            bool    `json:"is_paradox"`
	Color                *string `json:"color"`
	Shape                *string `json:"shape"`
	Habitat              *string `json:"habitat"`
}

type CompetitivePokemon struct {
	Name       string   `json:"name"`
	NationalNo *string  `json:"national_no"`
	Types      []string `json:"types"`
	Abilities  []string `json:"abilities"`
	HP         *int     `json:"hp"`
	Attack     *int     `json:"attack"`
	Defense    *int     `json:"defense"`
	SpAtk      *int     `json:"sp_atk"`
	SpDef      *int     `json:"sp_def"`
	Speed      *int     `json:"speed"`
	Total      *int     `json:"total"`
}

type ZMove struct {
	Name      string  `json:"name"`
	Type      *string `json:"type"`
	Power     *int    `json:"power"`
	Effect    *string `json:"effect"`
	BaseMove  *string `json:"base_move"`
	Category  *string `json:"category"`
}

type InGameTrade struct {
	Game             string  `json:"game"`
	Location         *string `json:"location"`
	OfferedPokemon   string  `json:"offered_pokemon"`
	OfferedLevel     *int    `json:"offered_level"`
	OfferedItem      *string `json:"offered_item"`
	RequestedPokemon string  `json:"requested_pokemon"`
	NpcName          *string `json:"npc_name"`
	Notes            *string `json:"notes"`
}

type ContestStat struct {
	PokemonName string `json:"pokemon_name"`
	ContestType string `json:"contest_type"`
	Appeal      *int   `json:"appeal"`
	Jam         *int   `json:"jam"`
}

type EventPokemon struct {
	Name               string   `json:"name"`
	Game               *string  `json:"game"`
	Year               *int     `json:"year"`
	Level              *int     `json:"level"`
	HeldItem           *string  `json:"held_item"`
	Moves              []string `json:"moves"`
	OtName             *string  `json:"ot_name"`
	DistributionMethod *string  `json:"distribution_method"`
	Notes              *string  `json:"notes"`
}

type MassOutbreak struct {
	Game        string  `json:"game"`
	Region      *string `json:"region"`
	Location    *string `json:"location"`
	PokemonName string  `json:"pokemon_name"`
	Notes       *string `json:"notes"`
}

type PokemonGo struct {
	PokemonName     string `json:"pokemon_name"`
	MaxCP           *int   `json:"max_cp"`
	BuddyDistanceKm *int   `json:"buddy_distance_km"`
	BaseAttack      *int   `json:"base_attack"`
	BaseDefense     *int   `json:"base_defense"`
	BaseStamina     *int   `json:"base_stamina"`
	ShinyAvailable  bool   `json:"shiny_available"`
	ShadowAvailable bool   `json:"shadow_available"`
}

type BattleFacility struct {
	Name         string  `json:"name"`
	Game         string  `json:"game"`
	Region       *string `json:"region"`
	FacilityType *string `json:"facility_type"`
	Description  *string `json:"description"`
	Currency     *string `json:"currency"`
}

type MoveTutorLocation struct {
	MoveName string  `json:"move_name"`
	Game     string  `json:"game"`
	Location *string `json:"location"`
	Cost     *string `json:"cost"`
}

type VersionExclusive struct {
	PokemonName string  `json:"pokemon_name"`
	Game        string  `json:"game"`
	GamePair    *string `json:"game_pair"`
}

type Trainer struct {
	Name           string  `json:"name"`
	Game           string  `json:"game"`
	Role           *string `json:"role"`
	SpecialtyType  *string `json:"specialty_type"`
	Location       *string `json:"location"`
	BattleVariant  string  `json:"battle_variant"`
}

type TrainerPokemon struct {
	TrainerName   string   `json:"trainer_name"`
	Game          string   `json:"game"`
	BattleVariant string   `json:"battle_variant"`
	PokemonName   string   `json:"pokemon_name"`
	Level         *int     `json:"level"`
	HeldItem      *string  `json:"held_item"`
	Ability       *string  `json:"ability"`
	Moves         []string `json:"moves"`
	TeamOrder     int      `json:"team_order"`
}
